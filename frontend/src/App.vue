<template>
  <div id="layout">
    <a href="#main" class="skip-link">{{ t('app.skip') }}</a>
    <div v-if="notice" class="realtime-notice" role="status" aria-live="polite">{{ notice }}</div>
    <NavBar />
    <main id="main" class="container" tabindex="-1">
      <router-view />
    </main>
    <footer class="footer">
      <p>{{ t('app.footer') }}</p>
    </footer>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import NavBar from './components/NavBar.vue'
import { connectSocket, disconnectSocket } from './utils/realtime'

const { t } = useI18n()
// WebSocket 实时通知条：收到评论/新文章广播时短暂展示
const notice = ref('')
let timer = null
function showNotice(msg) {
  notice.value = msg
  if (timer) clearTimeout(timer)
  timer = setTimeout(() => { notice.value = '' }, 3000)
}

onMounted(() => {
  connectSocket((type, data) => {
    if (type === 'comment') showNotice(t('app.newComment', { content: data.content || '' }))
    else if (type === 'post') showNotice(t('app.newPost', { title: data.title || '' }))
  })
})
onUnmounted(disconnectSocket)
</script>

<style>
/* #59 暗色模式：CSS 变量。亮/暗两套色板，组件只引用 var(--*)，切换 data-theme 即整体换肤。 */
:root {
  --bg: #f5f5f5; --fg: #333; --card-bg: #fff; --border: #eee; --border-strong: #ddd;
  --heading: #2c3e50; --muted: #999; --muted-strong: #666; --accent: #e74c3c; --accent-hover: #c0392b;
  --chip-bg: #fdecea; --tag-bg: #eef3ff; --tag-fg: #3a6ea5; --primary: #409eff;
  --skeleton: #e5e6eb; --shadow: rgba(0,0,0,0.06); --notice-bg: #2c3e50; --notice-fg: #fff;
  --input-bg: #fff; --thead-bg: #f8f9fa; --disabled: #c0c4cc; --danger-bg: #fde8e8; --success-bg: #e6f6ee;
  --mask: rgba(0,0,0,.4); --dash: #f0f0f0;
}
[data-theme="dark"] {
  --bg: #121212; --fg: #e2e2e2; --card-bg: #1e1e1e; --border: #333; --border-strong: #444;
  --heading: #ececec; --muted: #8a8a8a; --muted-strong: #b4b4b4; --accent: #ff6b5e; --accent-hover: #ff5040;
  --chip-bg: #3a2626; --tag-bg: #1e2a3a; --tag-fg: #7fb0e0; --primary: #6aa7ff;
  --skeleton: #333; --shadow: rgba(0,0,0,0.5); --notice-bg: #1a1a1a; --notice-fg: #fff;
  --input-bg: #242424; --thead-bg: #2a2a2a; --disabled: #4a4a4a; --danger-bg: #3a2222; --success-bg: #1e3327;
  --mask: rgba(0,0,0,.6); --dash: #333;
}
html { color-scheme: light; }
html[data-theme="dark"] { color-scheme: dark; }
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: var(--bg);
  color: var(--fg);
}
/* a11y：键盘可见焦点（不打断鼠标用户，仅 Tab 导航时显示） */
:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.skip-link {
  position: absolute; left: -9999px; top: 0;
  background: var(--accent); color: #fff; padding: 8px 16px; z-index: 1000;
}
.skip-link:focus { left: 0; }
.container { max-width: 960px; margin: 40px auto; padding: 0 20px; min-height: 70vh; }
.footer { text-align: center; padding: 20px; color: var(--muted); border-top: 1px solid var(--border); }
.section-title { margin-bottom: 20px; color: var(--heading); }
.card-category {
  display: inline-block; background: var(--chip-bg); color: var(--accent);
  font-size: 12px; padding: 2px 10px; border-radius: 12px; margin-bottom: 8px;
}
.realtime-notice { position: fixed; top: 0; left: 0; right: 0; z-index: 999; text-align: center; padding: 10px; background: var(--notice-bg); color: var(--notice-fg); font-size: 14px; }
.article-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }
.article-card {
  background: var(--card-bg); border-radius: 10px; padding: 20px;
  box-shadow: 0 2px 8px var(--shadow); transition: transform .15s;
}
.article-card:hover { transform: translateY(-3px); }
.card-link { text-decoration: none; color: inherit; display: block; }
.card-content h3 { margin-bottom: 8px; color: var(--heading); }
.card-content p { color: var(--muted-strong); font-size: 14px; margin-bottom: 10px; }
.card-date { color: var(--muted); font-size: 13px; }
.empty-tip { color: var(--muted); text-align: center; padding: 40px 0; }
.pagination { margin-top: 30px; text-align: center; }
.pagination a, .pagination .current {
  display: inline-block; margin: 0 4px; padding: 6px 12px;
  border: 1px solid var(--border-strong); border-radius: 6px; text-decoration: none; color: var(--fg); background: var(--card-bg); cursor: pointer;
}
.pagination .current { background: var(--accent); color: #fff; border-color: var(--accent); }
.auth-form { max-width: 420px; margin: 0 auto; background: var(--card-bg); padding: 30px; border-radius: 10px; box-shadow: 0 2px 8px var(--shadow); }
.auth-form h2 { margin-bottom: 20px; }
.form-group { margin-bottom: 16px; }
.form-group label { display: block; margin-bottom: 6px; font-size: 14px; }
.form-input { width: 100%; padding: 8px 12px; border: 1px solid var(--border-strong); border-radius: 6px; font-size: 14px; background: var(--input-bg); color: var(--fg); }
.btn-submit {
  width: 100%; padding: 10px; background: var(--accent); color: #fff;
  border: none; border-radius: 6px; cursor: pointer; font-size: 15px;
}
.btn-submit:hover { background: var(--accent-hover); }
.btn-submit:disabled { opacity: .6; cursor: not-allowed; }
.form-footer { margin-top: 14px; text-align: center; font-size: 14px; }
.form-footer a { color: var(--accent); }
.field-error { color: var(--accent); font-size: 13px; display: block; margin-top: 4px; }
.error-tip { color: var(--accent); font-size: 14px; margin-bottom: 12px; }
.category-bar { margin-bottom: 16px; }
.category-bar a {
  display: inline-block; margin-right: 8px; padding: 6px 14px;
  border-radius: 20px; background: var(--card-bg); text-decoration: none; color: var(--fg); border: 1px solid var(--border-strong);
}
.category-bar a.active { background: var(--accent); color: #fff; border-color: var(--accent); }
.search-bar { margin-bottom: 16px; }
.search-input { padding: 8px 14px; width: 100%; max-width: 420px; border: 1px solid var(--border-strong); border-radius: 6px; background: var(--input-bg); color: var(--fg); }
.detail-title { font-size: 26px; margin-bottom: 10px; }
.detail-meta { color: var(--muted); font-size: 14px; margin-bottom: 20px; }
.detail-content { background: var(--card-bg); padding: 30px; border-radius: 10px; line-height: 1.8; }
.fav-btn {
  padding: 8px 16px; background: var(--card-bg); border: 1px solid var(--accent); color: var(--accent);
  border-radius: 6px; cursor: pointer; margin-top: 24px;
}
.fav-btn.active { background: var(--accent); color: #fff; }
.fav-btn:disabled { opacity: .6; cursor: not-allowed; }
</style>
