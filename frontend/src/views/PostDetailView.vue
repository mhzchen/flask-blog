<template>
  <div v-if="post">
    <h1 class="detail-title">{{ post.title }}</h1>
    <div class="detail-meta">
      <span>{{ post.category }}</span>
      <span> | {{ post.created_at }}</span>
    </div>
    <div class="detail-content" v-html="post.content"></div>

    <template v-if="auth.isAuthenticated">
      <button class="fav-btn" :class="{ active: favorited }" :disabled="favLoading" @click="toggleFavorite">
        {{ favorited ? '已收藏 ♥' : '收藏 ♡' }}
      </button>
    </template>
    <p v-else class="empty-tip">
      登录后即可收藏文章。
    </p>
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

onMounted(fetchPost)
</script>