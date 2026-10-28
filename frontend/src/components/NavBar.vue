<template>
  <header class="navbar">
    <router-link to="/" class="logo">RUNOOB 博客</router-link>
    <nav>
      <router-link to="/">首页</router-link>
      <template v-if="auth.isAuthenticated">
        <span class="user-name">{{ auth.user?.username }}</span>
        <router-link to="/favorites">我的收藏</router-link>
        <a href="#" @click.prevent="handleLogout">登出</a>
      </template>
      <template v-else>
        <router-link to="/login">登录</router-link>
        <router-link to="/register">注册</router-link>
      </template>
    </nav>
  </header>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()

function handleLogout() {
  auth.logout()
  router.push('/')
}
</script>

<style scoped>
.navbar {
  display: flex; justify-content: space-between; align-items: center;
  padding: 16px 40px; background: #fff;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
.navbar .logo { font-size: 22px; font-weight: bold; color: #e74c3c; text-decoration: none; }
.navbar nav a, .navbar nav span { margin-left: 20px; text-decoration: none; color: #333; }
.navbar .user-name { color: #e74c3c; font-weight: bold; }
</style>