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
      this.setAuth(data.access_token, data.user)
      return data
    },
    async register(payload) {
      const { data } = await api.post('/auth/register', payload)
      this.setAuth(data.access_token, data.user)
      return data
    },
    setAuth(token, user) {
      this.token = token
      this.user = user
      localStorage.setItem('access_token', token)
      localStorage.setItem('user', JSON.stringify(user))
    },
    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem('access_token')
      localStorage.removeItem('user')
    },
  },
})