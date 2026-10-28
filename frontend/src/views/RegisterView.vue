<template>
  <div class="auth-form">
    <h2>注册</h2>
    <p v-if="error" class="error-tip">{{ error }}</p>
    <form @submit.prevent="handleRegister">
      <div class="form-group">
        <label>用户名</label>
        <input v-model="username" type="text" class="form-input" required minlength="3" />
      </div>
      <div class="form-group">
        <label>邮箱</label>
        <input v-model="email" type="email" class="form-input" required />
      </div>
      <div class="form-group">
        <label>密码</label>
        <input v-model="password" type="password" class="form-input" required minlength="6" />
      </div>
      <div class="form-group">
        <label>确认密码</label>
        <input v-model="confirmPassword" type="password" class="form-input" required />
        <span v-if="password && confirmPassword && password !== confirmPassword" class="field-error">两次输入的密码不一致</span>
      </div>
      <button type="submit" class="btn-submit" :disabled="loading">{{ loading ? '注册中...' : '注册' }}</button>
    </form>
    <p class="form-footer">已有账号？<router-link to="/login">立即登录</router-link></p>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()

const username = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const loading = ref(false)
const error = ref('')

async function handleRegister() {
  if (password.value !== confirmPassword.value) {
    error.value = '两次输入的密码不一致'
    return
  }
  loading.value = true
  error.value = ''
  try {
    await auth.register({ username: username.value, email: email.value, password: password.value })
    router.push('/')
  } catch (e) {
    error.value = e.response?.data?.error || '注册失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>