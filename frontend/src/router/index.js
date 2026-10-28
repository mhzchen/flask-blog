import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import PostDetailView from '../views/PostDetailView.vue'
import LoginView from '../views/LoginView.vue'
import RegisterView from '../views/RegisterView.vue'
import FavoritesView from '../views/FavoritesView.vue'
import AdminView from '../views/AdminView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/post/:id', name: 'post-detail', component: PostDetailView },
    { path: '/login', name: 'login', component: LoginView },
    { path: '/register', name: 'register', component: RegisterView },
    { path: '/favorites', name: 'favorites', component: FavoritesView, meta: { requiresAuth: true } },
    { path: '/admin', name: 'admin', component: AdminView, meta: { requiresAuth: true, requiresAdmin: true } },
  ],
})

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