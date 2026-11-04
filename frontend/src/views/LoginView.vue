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
    <div class="oauth-divider"><span>{{ t('auth.githubNote') }}</span></div>
    <a class="btn-github" href="/api/v1/auth/github/login">{{ t('auth.githubLogin') }}</a>
    <p class="form-footer">{{ t('auth.noAccount') }}<router-link to="/register">{{ t('auth.registerNow') }}</router-link></p>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
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

// GitHub OAuth 回调：后端 302 到 /?oauth=github&access_token=.. 后，落地登录态并跳回
onMounted(async () => {
  const oauthUser = await auth.completeOAuth()
  if (oauthUser) router.push(route.query.redirect || '/')
})
</script>

<style scoped>
.oauth-divider {
  margin: 18px 0 10px; text-align: center; color: var(--muted); font-size: 13px;
  display: flex; align-items: center; gap: 10px;
}
.oauth-divider::before, .oauth-divider::after {
  content: ''; flex: 1; height: 1px; background: var(--border);
}
.btn-github {
  display: block; text-align: center; width: 100%; padding: 10px;
  background: #24292f; color: #fff; border-radius: 6px; text-decoration: none;
  font-size: 15px; margin-bottom: 16px;
}
.btn-github:hover { background: #3b444f; }
</style>
