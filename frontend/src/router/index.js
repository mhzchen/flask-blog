import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/post/:id', name: 'post-detail', component: () => import('../views/PostDetailView.vue') },
    { path: '/login', name: 'login', component: () => import('../views/LoginView.vue') },
    { path: '/register', name: 'register', component: () => import('../views/RegisterView.vue') },
    { path: '/favorites', name: 'favorites', component: () => import('../views/FavoritesView.vue'), meta: { requiresAuth: true } },
    { path: '/admin', name: 'admin', component: () => import('../views/AdminView.vue'), meta: { requiresAuth: true, requiresAdmin: true } },
    { path: '/vitals', name: 'vitals', component: () => import('../views/VitalsView.vue') },
  ],
})

// LCP 优化：首页首屏直达（静态 import），首屏渲染空闲后预取热路由 chunk（文章详情/登录），
// 降低后续导航的加载延迟，也避免首页首屏多等一个异步 chunk。
if ('requestIdleCallback' in window) {
  requestIdleCallback(() => {
    Promise.all([
      import('../views/PostDetailView.vue'),
      import('../views/LoginView.vue'),
    ]).catch(() => {})
  })
}

// 全局前置守卫：需要登录的页面检查 token
router.beforeEach((to) => {
  const token = localStorage.getItem('access_token')
  if (to.meta.requiresAuth && !token) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.meta.requiresAdmin) {
    const user = JSON.parse(localStorage.getItem('user') || 'null')
    if (!user?.is_admin) {
      return { name: 'home' }
    }
  }
})

export default router