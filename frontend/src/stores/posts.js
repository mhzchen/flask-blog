import { defineStore } from 'pinia'
import api from '../api'

/**
 * 文章列表域 store（Pinia 模块化）：
 * 把 Home 的文章列表、分页、分类、标签的获取与状态集中管理，
 * 视图层只声明使用，不在组件内散落数据获取逻辑。
 */
export const usePostsStore = defineStore('posts', {
  state: () => {
    let saved = {}
    try {
      saved = JSON.parse(localStorage.getItem('posts_filter') || '{}')
    } catch {
      saved = {}
    }
    return {
      items: [],
      total: 0,
      pages: 0,
      hasPrev: false,
      hasNext: false,
      page: Number(saved.page) || 1,
      loading: false,
      categories: [],
      tags: [],
      keyword: saved.keyword || '',
      categorySlug: saved.categorySlug || '',
      tagName: saved.tagName || '',
    }
  },
  actions: {
    /** 把当前筛选条件（关键词/分类/标签/页码）写入 localStorage，下次进入自动恢复。 */
    _persistFilter() {
      try {
        localStorage.setItem('posts_filter', JSON.stringify({
          keyword: this.keyword,
          categorySlug: this.categorySlug,
          tagName: this.tagName,
          page: this.page,
        }))
      } catch { /* localStorage 不可用时静默跳过 */ }
    },
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
        this._persistFilter()
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
      this._persistFilter()
    },
  },
})
