import { defineStore } from 'pinia'
import api from '../api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('access_token') || '',
    user: JSON.parse(localStorage.getItem('user') || 'null'),
  }),
  getters: {
    isAuthenticated: (state) => !!state.token,
  },
  actions: {
    async login(username, password) {
      const { data } = await api.post('/auth/login', { username, password })
      this.setAuth(data.access_token, data.refresh_token, data.user)
      return data
    },
    async register(payload) {
      const { data } = await api.post('/auth/register', payload)
      this.setAuth(data.access_token, data.refresh_token, data.user)
      return data
    },
    setAuth(token, refreshToken, user) {
      this.token = token
      this.user = user
      localStorage.setItem('access_token', token)
      if (refreshToken) localStorage.setItem('refresh_token', refreshToken)
      localStorage.setItem('user', JSON.stringify(user))
    },
    // GitHub OAuth 回调处理：从 URL query 取 token，拉取用户信息后落地登录态
    async completeOAuth() {
      const qp = new URLSearchParams(window.location.search)
      if (qp.get('oauth') !== 'github' || !qp.get('access_token')) return null
      const token = qp.get('access_token')
      const refresh = qp.get('refresh_token') || ''
      this.token = token
      this.user = null
      localStorage.setItem('access_token', token)
      if (refresh) localStorage.setItem('refresh_token', refresh)
      try {
        const { data } = await api.get('/auth/me', { headers: { Authorization: `Bearer ${token}` } })
        this.user = data.user
        localStorage.setItem('user', JSON.stringify(data.user))
      } catch (e) { /* 用户信息未取到则仅保留 token，下次进入再补 */ }
      history.replaceState({}, '', window.location.pathname)
      return this.user
    },
    async refreshToken() {
      const refresh = localStorage.getItem('refresh_token')
      if (!refresh) throw new Error('no refresh token')
      const { data } = await api.post('/auth/refresh', null, {
        headers: { Authorization: `Bearer ${refresh}` },
        _skipAuth: true,
      })
      this.setAuth(data.access_token, null, this.user)
      return data.access_token
    },
    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('user')
    },
  },
})