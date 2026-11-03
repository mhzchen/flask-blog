import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  // 手动分包：把 vue 生态与 axios 拆成独立 vendor chunk，主包更小、缓存复用更好。
  // 各 view 已由路由动态 import 懒加载，分包后首屏只加载必要 chunk。
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'vue-vendor': ['vue', 'vue-router', 'pinia'],
          'axios': ['axios'],
        },
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['tests/**/*.test.js'],
  },
  server: {
    port: 5173,
    // 开发时把 /api 请求代理到 Flask 后端，避免跨域
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
    },
  },
})