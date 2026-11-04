<template>
  <div class="auth-form">
    <h1>{{ t('auth.login') }}</h1>
    <p v-if="error" class="error-tip" role="alert">{{ error }}</p>
    <form @submit.prevent="handleLogin">
      <div class="form-group">
        <label for="login-username">{{ t('auth.username') }}</label>
        <input id="login-username" v-model="username" type="text" class="form-input" :autocomplete="'username'" required />
      </div>
      <div class="form-group">
        <label for="login-password">{{ t('auth.password') }}</label>
        <input id="login-password" v-model="password" type="password" class="form-input" :autocomplete="'current-password'" required />
      </div>
      <button type="submit" class="btn-submit" :disabled="loading">{{ loading ? t('auth.loggingIn') : t('auth.login') }}</button>
    </form>
    <p class="form-footer">{{ t('auth.noAccount') }}<router-link to="/register">{{ t('auth.registerNow') }}</router-link></p>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'

const { t } = useI18n()
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
    error.value = e.response?.data?.error || t('auth.loginFailed')
  } finally {
    loading.value = false
  }
}
</script>
