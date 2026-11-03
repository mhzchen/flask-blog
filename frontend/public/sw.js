// Flask-Blog PWA Service Worker：离线缓存 + 运行时策略
// 策略：静态资源/页面 cache-first；GET /api/* 网络优先、离线回退缓存；页面兜底 index.html。
const CACHE = 'flask-blog-v1'
const PRECACHE = ['/', '/index.html']

self.addEventListener('install', (e) => {
  self.skipWaiting()
  e.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(PRECACHE)).catch(() => {})
  )
})

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  )
})

self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET') return
  const url = new URL(e.request.url)
  if (url.origin !== self.location.origin && !url.pathname.startsWith('/api/')) return

  // API 请求：网络优先，成功则写入缓存；失败（离线）回退缓存（历史数据可读）
  if (url.pathname.startsWith('/api/')) {
    e.respondWith(
      fetch(e.request)
        .then((res) => {
          if (res.ok) {
            const copy = res.clone()
            caches.open(CACHE).then((c) => c.put(e.request, copy))
          }
          return res
        })
        .catch(() => caches.match(e.request))
    )
    return
  }

  // 静态资源/页面：cache-first，未命中则网络并缓存；兜底 index.html（SPA 离线可达）
  e.respondWith(
    caches.match(e.request).then((hit) => hit || fetch(e.request).then((res) => {
      if (res.ok) {
        const copy = res.clone()
        caches.open(CACHE).then((c) => c.put(e.request, copy))
      }
      return res
    }).catch(() => caches.match('/index.html')))
  )
})