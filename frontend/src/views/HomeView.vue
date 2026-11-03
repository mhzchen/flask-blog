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

    <div class="category-bar tag-bar">
      <a href="#" @click.prevent="selectTag('')" :class="{ active: !tagName }">全部标签</a>
      <a v-for="t in tags" :key="t.id" href="#"
         @click.prevent="selectTag(t.name)" :class="{ active: tagName === t.name }">
        {{ t.name }}
      </a>
    </div>

    <p class="result-info">共 {{ total }} 篇文章<template v-if="keyword">，搜索「{{ keyword }}」</template></p>

    <div v-if="loading" class="article-grid">
      <div v-for="n in 6" :key="n" class="skeleton-card">
        <div class="skeleton-line" style="width:70%;height:15px;"></div>
        <div class="skeleton-line" style="width:100%;height:12px;"></div>
        <div class="skeleton-line" style="width:55%;height:12px;"></div>
      </div>
    </div>
    <div v-else-if="posts.length" class="article-grid">
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
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { usePostsStore } from '../stores/posts'
import PostCard from '../components/PostCard.vue'

const route = useRoute()
const router = useRouter()
const store = usePostsStore()
// 视图层只声明 store 状态（Pinia 模块化），数据获取集中在 stores/posts.js
const {
  items: posts, categories, tags, total, pages, hasPrev, hasNext,
  page, loading, keyword, categorySlug, tagName,
} = storeToRefs(store)

// 进入页面时用 URL query 初始化筛选条件（支持分享/刷新保持状态）
store.keyword = route.query.q || ''
store.categorySlug = route.query.category || ''
store.tagName = route.query.tag || ''

function _query() {
  return {
    q: keyword.value || undefined,
    category: categorySlug.value || undefined,
    tag: tagName.value || undefined,
  }
}

function search() {
  store.resetPage()
  router.push({ name: 'home', query: _query() })
  store.fetchList()
}

function selectCategory(slug) {
  store.categorySlug = slug
  store.resetPage()
  router.push({ name: 'home', query: _query() })
  store.fetchList()
}

function selectTag(name) {
  store.tagName = name
  store.resetPage()
  router.push({ name: 'home', query: _query() })
  store.fetchList()
}

function goPage(n) {
  if (n < 1 || n > pages.value) return
  store.page = n
  router.push({ name: 'home', query: { ...route.query, page: n } })
  store.fetchList()
}

onMounted(() => {
  store.fetchCategories()
  store.fetchTags()
  store.fetchList()
})
</script>

<style scoped>
@keyframes skeleton-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: .35; }
}
.skeleton-card {
  background: #fff;
  border: 1px solid #eee;
  border-radius: 8px;
  padding: 16px;
  animation: skeleton-pulse 1.2s ease-in-out infinite;
}
.skeleton-line {
  background: #e5e6eb;
  border-radius: 4px;
  margin: 12px 0;
}
</style>