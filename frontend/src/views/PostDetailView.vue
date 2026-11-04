<template>
  <div v-if="loadingPost" class="detail-skeleton" aria-hidden="true">
    <div class="skeleton-line" style="width:60%;height:28px;"></div>
    <div class="skeleton-line" style="width:35%;height:14px;margin-top:14px;"></div>
    <div class="skeleton-line" style="width:100%;height:16px;margin-top:28px;"></div>
    <div class="skeleton-line" style="width:100%;height:16px;"></div>
    <div class="skeleton-line" style="width:90%;height:16px;"></div>
    <div class="skeleton-line" style="width:70%;height:16px;"></div>
  </div>
  <article v-else-if="post">
    <h1 class="detail-title">{{ post.title }}</h1>
    <div class="detail-meta">
      <span>{{ post.category }}</span>
      <span> | {{ post.created_at }}</span> <span>| {{ t('post.views', { n: post.views }) }}</span>
    </div>
    <div class="detail-content" v-html="safeContent"></div>
    <div v-if="post.tags && post.tags.length" class="detail-tags">
      <span v-for="t in post.tags" :key="t" class="detail-tag">{{ t }}</span>
    </div>

    <template v-if="auth.isAuthenticated">
      <button class="like-btn" :class="{ active: liked }" :disabled="likeLoading"
              :aria-pressed="liked" @click="toggleLike">
        {{ liked ? t('post.liked') : t('post.like') }} {{ post.like_count ?? 0 }}
      </button>
      <button class="fav-btn" :class="{ active: favorited }" :disabled="favLoading"
              :aria-pressed="favorited" @click="toggleFavorite">
        {{ favorited ? t('post.favorited') : t('post.favorite') }}
      </button>
    </template>
    <p v-else class="empty-tip">
      {{ t('post.loginToFav') }}
    </p>

    <!-- 评论区 -->
    <section class="comments" aria-label="Comments">
      <h3>{{ t('post.comments', { n: total || comments.length }) }}</h3>
      <ul v-if="comments.length" class="comment-list">
        <li v-for="c in comments" :key="c.id" class="comment-item">
          <div class="comment-head">
            <strong>{{ c.username }}</strong>
            <span>{{ c.created_at }}</span>
            <button v-if="auth.isAuthenticated" class="reply-btn" @click="startReply(c)">{{ t('post.reply') }}</button>
            <button v-if="canDelete(c)" class="del-btn" @click="removeComment(c.id)">{{ t('post.delete') }}</button>
          </div>
          <p class="comment-content">{{ c.content }}</p>
          <ul v-if="c.replies && c.replies.length" class="reply-list">
            <li v-for="r in c.replies" :key="r.id" class="reply-item">
              <div class="comment-head">
                <strong>{{ r.username }}</strong>
                <span>{{ r.created_at }}</span>
                <button v-if="canDelete(r)" class="del-btn" @click="removeComment(r.id)">{{ t('post.delete') }}</button>
              </div>
              <p class="comment-content">{{ r.content }}</p>
            </li>
          </ul>
        </li>
      </ul>
      <p v-else class="empty-tip">{{ t('post.noComments') }}</p>

      <div v-if="auth.isAuthenticated" class="comment-form">
        <div v-if="replyTo" class="reply-to">
          {{ t('post.replyToUser', { name: replyTo.username }) }}
          <button class="reply-cancel" @click="replyTo = null">{{ t('post.cancel') }}</button>
        </div>
        <label for="comment-text" class="visually-hidden">{{ t('post.commentPh') }}</label>
        <textarea id="comment-text" v-model="commentText" :placeholder="t('post.commentPh')" rows="3"></textarea>
        <button :disabled="!commentText.trim() || submitting" @click="submitComment">{{ t('post.submit') }}</button>
      </div>
      <button v-if="auth.isAuthenticated && hasMore" class="load-more" @click="loadMore">{{ t('post.loadMore') }}</button>
      <p v-else class="empty-tip">{{ t('post.loginToComment') }}</p>
    </section>
  </article>
  <p v-else class="empty-tip">{{ t('post.notFound') }}</p>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import api from '../api'
import { useAuthStore } from '../stores/auth'
import { sanitizeHtml } from '../utils/sanitize'

const { t } = useI18n()
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
    // SEO：文章详情动态覆盖 <title> 与 meta description（含 i18n 站点名）
    if (data.post.title) document.title = `${data.post.title} · RUNOOB 博客`
    if (data.post.summary) {
      let el = document.querySelector('meta[name="description"]')
      if (!el) {
        el = document.createElement('meta'); el.setAttribute('name', 'description'); document.head.appendChild(el)
      }
      el.setAttribute('content', data.post.summary)
    }
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
    alert(t('post.commentFail') + (e.response?.data?.error || ''))
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
  background: var(--skeleton);
  border-radius: 4px;
  margin: 12px 0;
  animation: skeleton-pulse 1.2s ease-in-out infinite;
}
.like-btn { margin-right: 8px; background: var(--card-bg); border: 1px solid var(--accent); color: var(--accent); padding: 6px 14px; border-radius: 6px; cursor: pointer; }
.like-btn.active { background: var(--accent); color: #fff; }
.detail-tags { margin: 12px 0; }
.detail-tag {
  display: inline-block; background: var(--tag-bg); color: var(--tag-fg);
  font-size: 13px; padding: 3px 10px; border-radius: 12px; margin-right: 8px;
}

.comments {
  margin-top: 32px;
  border-top: 1px solid var(--border);
  padding-top: 16px;
}
.comment-list {
  list-style: none;
  padding: 0;
}
.comment-item {
  padding: 10px 0;
  border-bottom: 1px dashed var(--dash);
}
.comment-head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--muted);
}
.comment-head strong {
  color: var(--fg);
}
.del-btn {
  margin-left: auto;
  background: none;
  border: none;
  color: var(--accent);
  cursor: pointer;
  font-size: 13px;
}
.comment-content {
  margin: 6px 0 0;
  color: var(--muted-strong);
  line-height: 1.6;
}
.comment-form {
  margin-top: 16px;
}
.comment-form textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--border-strong);
  border-radius: 6px;
  padding: 10px;
  font-size: 14px;
  resize: vertical;
  background: var(--input-bg);
  color: var(--fg);
}
.comment-form button {
  margin-top: 8px;
  background: var(--primary);
  color: #fff;
  border: none;
  padding: 8px 20px;
  border-radius: 6px;
  cursor: pointer;
}
.comment-form button:disabled {
  background: var(--disabled);
  cursor: not-allowed;
}
.reply-list { list-style: none; margin: 8px 0 0 24px; padding: 0; }
.reply-item { padding: 8px 0; border-left: 2px solid var(--border); padding-left: 12px; }
.reply-btn { background: none; border: none; color: var(--primary); cursor: pointer; font-size: 13px; margin-left: 8px; }
.reply-to { margin-bottom: 8px; font-size: 13px; color: var(--muted-strong); }
.reply-cancel { background: none; border: none; color: var(--muted); cursor: pointer; margin-left: 8px; }
.load-more { margin-top: 12px; background: var(--card-bg); border: 1px solid var(--border-strong); padding: 6px 16px; border-radius: 6px; cursor: pointer; color: var(--primary); }
.visually-hidden {
  position: absolute; width: 1px; height: 1px; margin: -1px;
  padding: 0; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0;
}
</style>
