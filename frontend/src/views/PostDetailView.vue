<template>
  <div v-if="loadingPost" class="detail-skeleton">
    <div class="skeleton-line" style="width:60%;height:28px;"></div>
    <div class="skeleton-line" style="width:35%;height:14px;margin-top:14px;"></div>
    <div class="skeleton-line" style="width:100%;height:16px;margin-top:28px;"></div>
    <div class="skeleton-line" style="width:100%;height:16px;"></div>
    <div class="skeleton-line" style="width:90%;height:16px;"></div>
    <div class="skeleton-line" style="width:70%;height:16px;"></div>
  </div>
  <div v-else-if="post">
    <h1 class="detail-title">{{ post.title }}</h1>
    <div class="detail-meta">
      <span>{{ post.category }}</span>
      <span> | {{ post.created_at }}</span> <span>| {{ post.views }} 阅读</span>
    </div>
    <div class="detail-content" v-html="safeContent"></div>
    <div v-if="post.tags && post.tags.length" class="detail-tags">       <span v-for="t in post.tags" :key="t" class="detail-tag">{{ t }}</span>     </div>

    <template v-if="auth.isAuthenticated">
      <button class="like-btn" :class="{ active: liked }" :disabled="likeLoading" @click="toggleLike">
        {{ liked ? '已赞 ♥' : '点赞 ♡' }} {{ post.like_count ?? 0 }}
      </button>
      <button class="fav-btn" :class="{ active: favorited }" :disabled="favLoading" @click="toggleFavorite">
        {{ favorited ? '已收藏 ♥' : '收藏 ♡' }}
      </button>
    </template>
    <p v-else class="empty-tip">
      登录后即可收藏文章。
    </p>

    <!-- 评论区 -->
    <section class="comments">
      <h3>评论 ({{ total || comments.length }})</h3>
      <ul v-if="comments.length" class="comment-list">
        <li v-for="c in comments" :key="c.id" class="comment-item">
          <div class="comment-head">
            <strong>{{ c.username }}</strong>
            <span>{{ c.created_at }}</span>
            <button v-if="auth.isAuthenticated" class="reply-btn" @click="startReply(c)">回复</button>
            <button v-if="canDelete(c)" class="del-btn" @click="removeComment(c.id)">删除</button>
          </div>
          <p class="comment-content">{{ c.content }}</p>
          <ul v-if="c.replies && c.replies.length" class="reply-list">
            <li v-for="r in c.replies" :key="r.id" class="reply-item">
              <div class="comment-head">
                <strong>{{ r.username }}</strong>
                <span>{{ r.created_at }}</span>
                <button v-if="canDelete(r)" class="del-btn" @click="removeComment(r.id)">删除</button>
              </div>
              <p class="comment-content">{{ r.content }}</p>
            </li>
          </ul>
        </li>
      </ul>
      <p v-else class="empty-tip">还没有评论，来抢沙发~</p>

      <div v-if="auth.isAuthenticated" class="comment-form">
        <div v-if="replyTo" class="reply-to">
          回复 <strong>{{ replyTo.username }}</strong>
          <button class="reply-cancel" @click="replyTo = null">取消</button>
        </div>
        <textarea v-model="commentText" placeholder="写下你的评论..." rows="3"></textarea>
        <button :disabled="!commentText.trim() || submitting" @click="submitComment">发表评论</button>
      </div>
      <button v-if="auth.isAuthenticated && hasMore" class="load-more" @click="loadMore">加载更多评论</button>
      <p v-else class="empty-tip">登录后即可发表评论。</p>
    </section>
  </div>
  <p v-else class="empty-tip">文章不存在或加载失败。</p>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api'
import { useAuthStore } from '../stores/auth'
import { sanitizeHtml } from '../utils/sanitize'

const route = useRoute()
const auth = useAuthStore()

const post = ref(null)
const loadingPost = ref(true)
// 纵深防御：内容渲染前二次净化（后端已净化，这里兜底历史/其他入口数据）
const safeContent = computed(() => (post.value ? sanitizeHtml(post.value.content) : ''))
const favorited = ref(false)
const favLoading = ref(false)
const liked = ref(false)
const likeLoading = ref(false)
const comments = ref([])
const commentText = ref('')
const submitting = ref(false)
const replyTo = ref(null)
const commentPage = ref(1)
const hasMore = ref(false)
const total = ref(0)

async function fetchPost() {
  loadingPost.value = true
  try {
    const { data } = await api.get(`/posts/${route.params.id}`)
    post.value = data.post
    liked.value = !!data.post.liked
    if (auth.isAuthenticated) {
      try {
        const { data: fav } = await api.get(`/favorites/check/${route.params.id}`)
        favorited.value = fav.favorited
      } catch (e) { /* 忽略 */ }
    }
  } finally {
    loadingPost.value = false
  }
}

async function toggleFavorite() {
  favLoading.value = true
  try {
    const { data } = await api.post(`/favorites/${route.params.id}/toggle`)
    favorited.value = data.favorited
  } catch (e) {
    // 401 已由拦截器处理跳转登录
  } finally {
    favLoading.value = false
  }
}

async function toggleLike() {
  likeLoading.value = true
  try {
    const { data } = await api.post(`/posts/${route.params.id}/like`)
    liked.value = data.liked
    post.value.like_count = data.like_count
  } catch (e) {
    // 401 已由拦截器处理跳转登录
  } finally {
    likeLoading.value = false
  }
}

async function fetchComments() {
  try {
    const { data } = await api.get(`/posts/${route.params.id}/comments`, { params: { page: 1, per_page: 20 } })
    comments.value = data.items
    commentPage.value = data.page
    total.value = data.total
    hasMore.value = data.page < data.pages
  } catch (e) { /* 忽略 */ }
}

async function loadMore() {
  try {
    const next = commentPage.value + 1
    const { data } = await api.get(`/posts/${route.params.id}/comments`, { params: { page: next, per_page: 20 } })
    comments.value = comments.value.concat(data.items)
    commentPage.value = data.page
    hasMore.value = data.page < data.pages
  } catch (e) { /* 忽略 */ }
}

function startReply(c) {
  replyTo.value = c
}

function insertComment(nc) {
  if (nc.parent_id) {
    const top = comments.value.find(c => c.id === nc.parent_id)
    if (top) { top.replies = top.replies || []; top.replies.push(nc) }
  } else {
    comments.value.push(nc)
  }
}

function canDelete(c) {
  return auth.isAuthenticated && (auth.user?.id === c.user_id || auth.user?.is_admin)
}

async function submitComment() {
  const content = commentText.value.trim()
  if (!content) return
  submitting.value = true
  try {
    const { data } = await api.post(`/posts/${route.params.id}/comments`, { content, parent_id: replyTo.value?.id || null })
    insertComment(data.comment)
    commentText.value = ''
    replyTo.value = null
  } catch (e) {
    alert('评论失败：' + (e.response?.data?.error || '请重试'))
  } finally {
    submitting.value = false
  }
}

async function removeComment(id) {
  try {
    await api.delete(`/comments/${id}`)
    comments.value = comments.value.filter(c => c.id !== id)
  } catch (e) { /* 忽略 */ }
}

onMounted(() => {
  fetchPost()
  fetchComments()
})
</script>

<style scoped>
.detail-skeleton { padding: 8px 0; }
@keyframes skeleton-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: .35; }
}
.detail-skeleton .skeleton-line {
  background: #e5e6eb;
  border-radius: 4px;
  margin: 12px 0;
  animation: skeleton-pulse 1.2s ease-in-out infinite;
}
.like-btn { margin-right: 8px; background: #fff; border: 1px solid #f0c; color: #e74c3c; padding: 6px 14px; border-radius: 6px; cursor: pointer; }
.detail-tags { margin: 12px 0; }
.detail-tag {
  display: inline-block; background: #eef3ff; color: #3a6ea5;
  font-size: 13px; padding: 3px 10px; border-radius: 12px; margin-right: 8px;
}

.comments {
  margin-top: 32px;
  border-top: 1px solid #eee;
  padding-top: 16px;
}
.comment-list {
  list-style: none;
  padding: 0;
}
.comment-item {
  padding: 10px 0;
  border-bottom: 1px dashed #f0f0f0;
}
.comment-head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #888;
}
.comment-head strong {
  color: #333;
}
.del-btn {
  margin-left: auto;
  background: none;
  border: none;
  color: #e74c3c;
  cursor: pointer;
  font-size: 13px;
}
.comment-content {
  margin: 6px 0 0;
  color: #444;
  line-height: 1.6;
}
.comment-form {
  margin-top: 16px;
}
.comment-form textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #ddd;
  border-radius: 6px;
  padding: 10px;
  font-size: 14px;
  resize: vertical;
}
.comment-form button {
  margin-top: 8px;
  background: #409eff;
  color: #fff;
  border: none;
  padding: 8px 20px;
  border-radius: 6px;
  cursor: pointer;
}
.comment-form button:disabled {
  background: #c0c4cc;
  cursor: not-allowed;
}
.reply-list { list-style: none; margin: 8px 0 0 24px; padding: 0; }
.reply-item { padding: 8px 0; border-left: 2px solid #eef; padding-left: 12px; }
.reply-btn { background: none; border: none; color: #409eff; cursor: pointer; font-size: 13px; margin-left: 8px; }
.reply-to { margin-bottom: 8px; font-size: 13px; color: #666; }
.reply-cancel { background: none; border: none; color: #999; cursor: pointer; margin-left: 8px; }
.load-more { margin-top: 12px; background: #fff; border: 1px solid #ddd; padding: 6px 16px; border-radius: 6px; cursor: pointer; color: #409eff; }
</style>