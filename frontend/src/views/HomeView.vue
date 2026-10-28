<template>
  <div>
    <h2 class="section-title">最新文章</h2>

    <div class="search-bar">
      <form @submit.prevent="search">
        <input v-model="keyword" type="text" placeholder="搜索文章标题或摘要..." class="search-input" />
        <button type="submit" class="btn-submit" style="width:auto;display:inline-block;margin-left:8px;padding:8px 16px;">搜索</button>
      </form>
    </div>

    <div class="category-bar">
      <a href="#" @click.prevent="selectCategory('')" :class="{ active: !categorySlug }">全部</a>
      <a v-for="cat in categories" :key="cat.id" href="#"
         @click.prevent="selectCategory(cat.slug)" :class="{ active: categorySlug === cat.slug }">
        {{ cat.name }}
      </a>
    </div>

    <p class="result-info">共 {{ total }} 篇文章<template v-if="keyword">，搜索「{{ keyword }}」</template></p>

    <div v-if="posts.length" class="article-grid">
      <PostCard v-for="post in posts" :key="post.id" :post="post" />
    </div>
    <p v-else class="empty-tip">没有找到匹配的文章。</p>

    <div v-if="pages > 1" class="pagination">
      <a href="#" @click.prevent="goPage(page - 1)" v-if="hasPrev">← 上一页</a>
      <template v-for="n in pages" :key="n">
        <span v-if="n === page" class="current">{{ n }}</span>
        <a v-else href="#" @click.prevent="goPage(n)">{{ n }}</a>
      </template>
      <a href="#" @click.prevent="goPage(page + 1)" v-if="hasNext">下一页 →</a>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api'
import PostCard from '../components/PostCard.vue'

const route = useRoute()
const router = useRouter()

const posts = ref([])
const categories = ref([])
const total = ref(0)
const page = ref(1)
const pages = ref(0)
const hasPrev = ref(false)
const hasNext = ref(false)
const keyword = ref(route.query.q || '')
const categorySlug = ref(route.query.category || '')

async function fetchData() {
  const { data } = await api.get('/posts', {
    params: {
      q: keyword.value || undefined,
      category: categorySlug.value || undefined,
      page: page.value,
    },
  })
  posts.value = data.items
  total.value = data.total
  pages.value = data.pages
  hasPrev.value = data.has_prev
  hasNext.value = data.has_next
}

async function fetchCategories() {
  const { data } = await api.get('/categories')
  categories.value = data.items
}

function search() {
  page.value = 1
  router.push({ name: 'home', query: { q: keyword.value || undefined, category: categorySlug.value || undefined } })
  fetchData()
}

function selectCategory(slug) {
  categorySlug.value = slug
  page.value = 1
  router.push({ name: 'home', query: { q: keyword.value || undefined, category: slug || undefined } })
  fetchData()
}

function goPage(n) {
  if (n < 1 || n > pages.value) return
  page.value = n
  router.push({ name: 'home', query: { ...route.query, page: n } })
  fetchData()
}

onMounted(() => {
  fetchCategories()
  fetchData()
})
</script>