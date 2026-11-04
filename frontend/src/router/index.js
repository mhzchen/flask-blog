import { createRouter, createWebHistory } from 'vue-router'
import i18n from '../i18n'
import HomeView from '../views/HomeView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView, meta: { titleKey: 'nav.home', desc: 'Flask + Vue3 全栈技术博客，分享 Web 开发、Python、JavaScript 实战经验' } },
    { path: '/post/:id', name: 'post-detail', component: () => import('../views/PostDetailView.vue'), meta: { titleKey: 'nav.postDetail', desc: '文章详情' } },
    { path: '/login', name: 'login', component: () => import('../views/LoginView.vue'), meta: { titleKey: 'nav.login', desc: '登录 RUNOOB 博客' } },
    { path: '/register', name: 'register', component: () => import('../views/RegisterView.vue'), meta: { titleKey: 'nav.register', desc: '注册 RUNOOB 博客' } },
    { path: '/favorites', name: 'favorites', component: () => import('../views/FavoritesView.vue'), meta: { requiresAuth: true, titleKey: 'nav.favorites', desc: '我的收藏' } },
    { path: '/admin', name: 'admin', component: () => import('../views/AdminView.vue'), meta: { requiresAuth: true, requiresAdmin: true, titleKey: 'nav.admin', desc: '后台管理' } },
    { path: '/vitals', name: 'vitals', component: () => import('../views/VitalsView.vue'), meta: { titleKey: 'nav.vitals', desc: 'Web Vitals 性能指标' } },
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

// SEO：每次路由切换同步 <title> 与 <meta name="description">（支持 i18n 标题）
function setMeta(name, content) {
  let el = document.querySelector(`meta[name="${name}"]`)
  if (!el) {
    el = document.createElement('meta')
    el.setAttribute('name', name)
    document.head.appendChild(el)
  }
  el.setAttribute('content', content)
}

router.afterEach((to) => {
  const t = i18n.global.t
  const title = to.meta.titleKey ? t(to.meta.titleKey) : ''
  document.title = title ? `${title} · RUNOOB 博客` : 'RUNOOB 博客'
  if (to.meta.desc) setMeta('description', to.meta.desc)
})

export default router