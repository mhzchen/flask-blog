import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { onCLS, onFCP, onINP, onLCP, onTTFB } from 'web-vitals'
import App from './App.vue'
import router from './router'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')

// Web Vitals 采集上报：CLS / FCP / INP / LCP / TTFB
// 通过 sendBeacon 异步投递到后端 /api/vitals（页面卸载时也能送达），生产低开销。
function reportVitals(metric) {
  const payload = JSON.stringify({
    name: metric.name,
    value: metric.value,
    rating: metric.rating,
    navigationType: metric.navigationType || '',
  })
  if (navigator.sendBeacon) {
    navigator.sendBeacon('/api/vitals', new Blob([payload], { type: 'application/json' }))
  } else {
    fetch('/api/vitals', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: payload,
      keepalive: true,
    }).catch(() => {})
  }
  if (import.meta.env.DEV) {
    console.log(`[web-vitals] ${metric.name}: ${metric.value.toFixed(2)} (${metric.rating})`)
  }
}

onCLS(reportVitals)
onFCP(reportVitals)
onINP(reportVitals)
onLCP(reportVitals)
onTTFB(reportVitals)
