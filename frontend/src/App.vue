<template>
  <div id="layout">
    <NavBar />
    <main class="container">
      <router-view />
    </main>
    <footer class="footer">
      <p>© 2026 RUNOOB 博客 · Flask + Vue3</p>
    </footer>
  </div>
</template>

<script setup>
import NavBar from './components/NavBar.vue'
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #f5f5f5;
  color: #333;
}
.container { max-width: 960px; margin: 40px auto; padding: 0 20px; min-height: 70vh; }
.footer { text-align: center; padding: 20px; color: #999; border-top: 1px solid #eee; }
.section-title { margin-bottom: 20px; color: #2c3e50; }
.card-category {
  display: inline-block; background: #fdecea; color: #e74c3c;
  font-size: 12px; padding: 2px 10px; border-radius: 12px; margin-bottom: 8px;
}
.article-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }
.article-card {
  background: #fff; border-radius: 10px; padding: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06); transition: transform .15s;
}
.article-card:hover { transform: translateY(-3px); }
.card-link { text-decoration: none; color: inherit; display: block; }
.card-content h3 { margin-bottom: 8px; color: #2c3e50; }
.card-content p { color: #666; font-size: 14px; margin-bottom: 10px; }
.card-date { color: #aaa; font-size: 13px; }
.empty-tip { color: #999; text-align: center; padding: 40px 0; }
.pagination { margin-top: 30px; text-align: center; }
.pagination a, .pagination .current {
  display: inline-block; margin: 0 4px; padding: 6px 12px;
  border: 1px solid #ddd; border-radius: 6px; text-decoration: none; color: #333; background: #fff; cursor: pointer;
}
.pagination .current { background: #e74c3c; color: #fff; border-color: #e74c3c; }
.auth-form { max-width: 420px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 10px; }
.auth-form h2 { margin-bottom: 20px; }
.form-group { margin-bottom: 16px; }
.form-group label { display: block; margin-bottom: 6px; font-size: 14px; }
.form-input { width: 100%; padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; }
.btn-submit {
  width: 100%; padding: 10px; background: #e74c3c; color: #fff;
  border: none; border-radius: 6px; cursor: pointer; font-size: 15px;
}
.btn-submit:hover { background: #c0392b; }
.btn-submit:disabled { opacity: .6; cursor: not-allowed; }
.form-footer { margin-top: 14px; text-align: center; font-size: 14px; }
.form-footer a { color: #e74c3c; }
.field-error { color: #e74c3c; font-size: 13px; display: block; margin-top: 4px; }
.error-tip { color: #e74c3c; font-size: 14px; margin-bottom: 12px; }
.category-bar { margin-bottom: 16px; }
.category-bar a {
  display: inline-block; margin-right: 8px; padding: 6px 14px;
  border-radius: 20px; background: #fff; text-decoration: none; color: #333; border: 1px solid #ddd;
}
.category-bar a.active { background: #e74c3c; color: #fff; border-color: #e74c3c; }
.search-bar { margin-bottom: 16px; }
.search-input { padding: 8px 14px; width: 100%; max-width: 420px; border: 1px solid #ddd; border-radius: 6px; }
.detail-title { font-size: 26px; margin-bottom: 10px; }
.detail-meta { color: #999; font-size: 14px; margin-bottom: 20px; }
.detail-content { background: #fff; padding: 30px; border-radius: 10px; line-height: 1.8; }
.fav-btn {
  padding: 8px 16px; background: #fff; border: 1px solid #e74c3c; color: #e74c3c;
  border-radius: 6px; cursor: pointer; margin-top: 24px;
}
.fav-btn.active { background: #e74c3c; color: #fff; }
.fav-btn:disabled { opacity: .6; cursor: not-allowed; }
</style>