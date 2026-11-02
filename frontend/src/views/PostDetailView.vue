<template>
  <div v-if="post">
    <h1 class="detail-title">{{ post.title }}</h1>
    <div class="detail-meta">
      <span>{{ post.category }}</span>
      <span> | {{ post.created_at }}</span>
    </div>
    <div class="detail-content" v-html="post.content"></div>
    <div v-if="post.tags && post.tags.length" class="detail-tags">       <span v-for="t in post.tags" :key="t" class="detail-tag">{{ t }}</span>     </div>

    <template v-if="auth.isAuthenticated">
      <button class="fav-btn" :class="{ active: favorited }" :disabled="favLoading" @click="toggleFavorite">
        {{ favorited ? '已收藏 ♥' : '收藏 ♡' }}
      </button>
    </template>
    <p v-else class="empty-tip">
      登录后即可收藏文章。
    </p>

    <!-- 评论区 -->
    <section class="comments">
      <h3>评论 ({{ comments.length }})</h3>
      <ul v-if="comments.length" class="comment-list">
        <li v-for="c in comments" :key="c.id" class="comment-item">
          <div class="comment-head">
            <strong>{{ c.username }}</strong>
            <span>{{ c.created_at }}</span>
            <button v-if="canDelete(c)" class="del-btn" @click="removeComment(c.id)">删除</button>
          </div>
          <p class="comment-content">{{ c.content }}</p>
        </li>
      </ul>
      <p v-else class="empty-tip">还没有评论，来抢沙发~</p>

      <div v-if="auth.isAuthenticated" class="comment-form">
        <textarea v-model="commentText" placeholder="写下你的评论..." rows="3"></textarea>
        <button :disabled="!commentText.trim() || submitting" @click="submitComment">发表评论</button>
      </div>
      <p v-else class="empty-tip">登录后即可发表评论。</p>
    </section>
  </div>
  <p v-else class="empty-tip">文章不存在或加载失败。</p>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const auth = useAuthStore()

const post = ref(null)
const favorited = ref(false)
const favLoading = ref(false)
const comments = ref([])
const commentText = ref('')
const submitting = ref(false)

async function fetchPost() {
  const { data } = await api.get(`/posts/${route.params.id}`)
  post.value = data.post
  if (auth.isAuthenticated) {
    try {
      const { data: fav } = await api.get(`/favorites/check/${route.params.id}`)
      favorited.value = fav.favorited
    } catch (e) { /* 忽略 */ }
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

async function fetchComments() {
  try {
    const { data } = await api.get(`/posts/${route.params.id}/comments`)
    comments.value = data.items
  } catch (e) { /* 忽略 */ }
}

function canDelete(c) {
  return auth.isAuthenticated && (auth.user?.id === c.user_id || auth.user?.is_admin)
}

async function submitComment() {
  const content = commentText.value.trim()
  if (!content) return
  submitting.value = true
  try {
    const { data } = await api.post(`/posts/${route.params.id}/comments`, { content })
    comments.value.push(data.comment)
    commentText.value = ''
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
</style>