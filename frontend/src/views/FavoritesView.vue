<template>
  <div>
    <h2 class="section-title">{{ t('fav.title') }}</h2>
    <div v-if="posts.length" class="article-grid">
      <PostCard v-for="post in posts" :key="post.id" :post="post" />
    </div>
    <p v-else class="empty-tip">{{ t('fav.none') }}</p>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '../api'
import PostCard from '../components/PostCard.vue'

const { t } = useI18n()
const posts = ref([])

async function fetchFavorites() {
  const { data } = await api.get('/favorites')
  posts.value = data.items
}

onMounted(fetchFavorites)
</script>
