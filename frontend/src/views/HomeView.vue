<template>
  <div>
    <h2 class="section-title">{{ t('home.latest') }}</h2>

    <div class="search-bar">
      <form @submit.prevent="search" role="search">
        <label for="search-input" class="visually-hidden">{{ t('home.searchPh') }}</label>
        <input id="search-input" v-model="keyword" type="text" :placeholder="t('home.searchPh')" class="search-input" />
        <button type="submit" class="btn-submit" style="width:auto;display:inline-block;margin-left:8px;padding:8px 16px;">{{ t('home.search') }}</button>
      </form>
    </div>

    <div class="category-bar">
      <a href="#" @click.prevent="selectCategory('')" :class="{ active: !categorySlug }">{{ t('home.all') }}</a>
      <a v-for="cat in categories" :key="cat.id" href="#"
         @click.prevent="selectCategory(cat.slug)" :class="{ active: categorySlug === cat.slug }">
        {{ cat.name }}
      </a>
    </div>

    <div class="category-bar tag-bar">
      <a href="#" @click.prevent="selectTag('')" :class="{ active: !tagName }">{{ t('home.allTags') }}</a>
      <a v-for="t in tags" :key="t.id" href="#"
         @click.prevent="selectTag(t.name)" :class="{ active: tagName === t.name }">
        {{ t.name }}
      </a>
    </div>

    <p class="result-info">
      {{ t('home.resultPrefix', { total }) }}<template v-if="keyword">{{ t('home.searchKw', { kw: keyword }) }}</template>
    </p>

    <div v-if="loading" class="article-grid" aria-hidden="true">
      <div v-for="n in 6" :key="n" class="skeleton-card">
        <div class="skeleton-line" style="width:70%;height:15px;"></div>
        <div class="skeleton-line" style="width:100%;height:12px;"></div>
        <div class="skeleton-line" style="width:55%;height:12px;"></div>
      </div>
    </div>
    <div v-else-if="posts.length" class="article-grid">
      <PostCard v-for="post in posts" :key="post.id" :post="post" />
    </div>
    <p v-else class="empty-tip">{{ t('home.noMatch') }}</p>

    <nav v-if="pages > 1" class="pagination" aria-label="Pagination">
      <a href="#" @click.prevent="goPage(page - 1)" v-if="hasPrev">{{ t('home.prev') }}</a>
      <template v-for="n in pages" :key="n">
        <span v-if="n === page" class="current" aria-current="page">{{ n }}</span>
        <a v-else href="#" @click.prevent="goPage(n)">{{ n }}</a>
      </template>
      <a href="#" @click.prevent="goPage(page + 1)" v-if="hasNext">{{ t('home.next') }}</a>
    </nav>

    <button v-if="hasMore" class="load-more" @click="store.loadMore()" :disabled="loadingMore">
      {{ loadingMore ? t('home.loadingMore') : t('home.loadMore') }}
    </button>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useI18n } from 'vue-i18n'
import { usePostsStore } from '../stores/posts'
import PostCard from '../components/PostCard.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const store = usePostsStore()
// 视图层只声明 store 状态（Pinia 模块化），数据获取集中在 stores/posts.js
const {
  items: posts, categories, tags, total, pages, hasPrev, hasNext,
  page, loading, hasMore, loadingMore, keyword, categorySlug, tagName,
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
.load-more {
  display: block; margin: 20px auto 0; padding: 8px 22px;
  background: var(--card-bg); border: 1px solid var(--border-strong);
  border-radius: 6px; color: var(--primary); cursor: pointer; font-size: 14px;
}
.load-more:disabled { opacity: .6; cursor: not-allowed; }

@keyframes skeleton-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: .35; }
}
.skeleton-card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
  animation: skeleton-pulse 1.2s ease-in-out infinite;
}
.skeleton-line {
  background: var(--skeleton);
  border-radius: 4px;
  margin: 12px 0;
}
.visually-hidden {
  position: absolute; width: 1px; height: 1px; margin: -1px;
  padding: 0; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0;
}
</style>
