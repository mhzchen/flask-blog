import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
})

// 请求拦截器：自动带上 JWT token（跳过 refresh 请求自身）
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token && !config._skipAuth) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 并发刷新：多个请求同时 401 时只发一次 refresh，其余等待同一个 Promise
let refreshPromise = null

async function doRefresh() {
  const refresh = localStorage.getItem('refresh_token')
  if (!refresh) throw new Error('no refresh token')
  const { data } = await axios.post('/api/v1/auth/refresh', null, {
    headers: { Authorization: `Bearer ${refresh}` },
  })
  localStorage.setItem('access_token', data.access_token)
  return data.access_token
}

// 响应拦截器：401 时用 refresh token 静默续期并重试原请求；刷新失败才登出
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    // 只有真正需要认证的接口才触发刷新；refresh 本身失败直接登出
    if (error.response?.status === 401 && !original._skipAuth && !original._retried) {
      try {
        original._retried = true
        if (!refreshPromise) {
          refreshPromise = doRefresh().finally(() => { refreshPromise = null })
        }
        const token = await refreshPromise
        original.headers.Authorization = `Bearer ${token}`
        return api(original)
      } catch (e) {
        // 刷新失败：清除凭证并跳转登录
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        localStorage.removeItem('user')
        if (window.location.pathname !== '/login') {
          window.location.href = '/login'
        }
        return Promise.reject(e)
      }
    }
    return Promise.reject(error)
  }
)

export default api