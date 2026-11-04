<template>
  <div class="auth-form">
    <h1>{{ t('auth.register') }}</h1>
    <p v-if="error" class="error-tip" role="alert">{{ error }}</p>
    <form @submit.prevent="handleRegister">
      <div class="form-group">
        <label for="reg-username">{{ t('auth.username') }}</label>
        <input id="reg-username" v-model="username" type="text" class="form-input" :autocomplete="'username'" required minlength="3" />
      </div>
      <div class="form-group">
        <label for="reg-email">{{ t('auth.email') }}</label>
        <input id="reg-email" v-model="email" type="email" class="form-input" :autocomplete="'email'" required />
      </div>
      <div class="form-group">
        <label for="reg-password">{{ t('auth.password') }}</label>
        <input id="reg-password" v-model="password" type="password" class="form-input" :autocomplete="'new-password'" required minlength="6" />
      </div>
      <div class="form-group">
        <label for="reg-confirm">{{ t('auth.confirm') }}</label>
        <input id="reg-confirm" v-model="confirmPassword" type="password" class="form-input" :autocomplete="'new-password'" required />
        <span v-if="password && confirmPassword && password !== confirmPassword" class="field-error" aria-live="polite">{{ t('auth.mismatch') }}</span>
      </div>
      <button type="submit" class="btn-submit" :disabled="loading">{{ loading ? t('auth.registering') : t('auth.register') }}</button>
    </form>
    <p class="form-footer">{{ t('auth.haveAccount') }}<router-link to="/login">{{ t('auth.loginNow') }}</router-link></p>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'

const { t } = useI18n()
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
    error.value = t('auth.mismatch')
    return
  }
  loading.value = true
  error.value = ''
  try {
    await auth.register({ username: username.value, email: email.value, password: password.value })
    router.push('/')
  } catch (e) {
    error.value = e.response?.data?.error || t('auth.registerFailed')
  } finally {
    loading.value = false
  }
}
</script>
