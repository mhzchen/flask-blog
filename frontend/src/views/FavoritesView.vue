<template>
  <div>
    <h2 class="section-title">我的收藏</h2>
    <div v-if="posts.length" class="article-grid">
      <PostCard v-for="post in posts" :key="post.id" :post="post" />
    </div>
    <p v-else class="empty-tip">你还没有收藏任何文章。</p>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api'
import PostCard from '../components/PostCard.vue'

const posts = ref([])

async function fetchFavorites() {
  const { data } = await api.get('/favorites')
  posts.value = data.items
}

onMounted(fetchFavorites)
</script>