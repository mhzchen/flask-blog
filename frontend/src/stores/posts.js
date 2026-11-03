import { defineStore } from 'pinia'
import api from '../api'

/**
 * 文章列表域 store（Pinia 模块化）：
 * 把 Home 的文章列表、分页、分类、标签的获取与状态集中管理，
 * 视图层只声明使用，不在组件内散落数据获取逻辑。
 */
export const usePostsStore = defineStore('posts', {
  state: () => ({
    items: [],
    total: 0,
    pages: 0,
    hasPrev: false,
    hasNext: false,
    page: 1,
    loading: false,
    categories: [],
    tags: [],
    keyword: '',
    categorySlug: '',
    tagName: '',
  }),
  actions: {
    /** 按当前筛选条件拉取文章列表（读接口，走后端分页/缓存）。 */
    async fetchList() {
      this.loading = true
      try {
        const { data } = await api.get('/posts', {
          params: {
            q: this.keyword || undefined,
            category: this.categorySlug || undefined,
            tag: this.tagName || undefined,
            page: this.page,
          },
        })
        this.items = data.items
        this.total = data.total
        this.pages = data.pages
        this.hasPrev = data.has_prev
        this.hasNext = data.has_next
      } finally {
        this.loading = false
      }
    },
    /** 拉取全部分类（侧栏筛选）。 */
    async fetchCategories() {
      const { data } = await api.get('/categories')
      this.categories = data.items
    },
    /** 拉取全部标签（侧栏筛选）。 */
    async fetchTags() {
      const { data } = await api.get('/tags')
      this.tags = data.items
    },
    /** 回到第一页（搜索/切换分类标签时调用）。 */
    resetPage() {
      this.page = 1
    },
  },
})
