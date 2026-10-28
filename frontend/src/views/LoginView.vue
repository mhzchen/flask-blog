<template>
  <div class="auth-form">
    <h2>登录</h2>
    <p v-if="error" class="error-tip">{{ error }}</p>
    <form @submit.prevent="handleLogin">
      <div class="form-group">
        <label>用户名</label>
        <input v-model="username" type="text" class="form-input" required />
      </div>
      <div class="form-group">
        <label>密码</label>
        <input v-model="password" type="password" class="form-input" required />
      </div>
      <button type="submit" class="btn-submit" :disabled="loading">{{ loading ? '登录中...' : '登录' }}</button>
    </form>
    <p class="form-footer">还没有账号？<router-link to="/register">立即注册</router-link></p>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

async function handleLogin() {
  loading.value = true
  error.value = ''
  try {
    await auth.login(username.value, password.value)
    router.push(route.query.redirect || '/')
  } catch (e) {
    error.value = e.response?.data?.error || '登录失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>