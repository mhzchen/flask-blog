<template>
  <header class="navbar">
    <router-link to="/" class="logo">RUNOOB 博客</router-link>
    <nav aria-label="Primary navigation">
      <router-link to="/">{{ t('nav.home') }}</router-link>
      <template v-if="auth.isAuthenticated">
        <span class="user-name">{{ auth.user?.username }}</span>
        <router-link v-if="auth.user?.is_admin" to="/admin">{{ t('nav.admin') }}</router-link>
        <router-link to="/favorites">{{ t('nav.favorites') }}</router-link>
        <button type="button" class="nav-btn" @click="handleLogout">{{ t('nav.logout') }}</button>
      </template>
      <template v-else>
        <router-link to="/login">{{ t('nav.login') }}</router-link>
        <router-link to="/register">{{ t('nav.register') }}</router-link>
      </template>
    </nav>
    <div class="nav-actions">
      <button type="button" class="icon-btn" :aria-label="t('nav.theme')" :title="t('nav.theme')" @click="onToggleTheme">
        {{ isDark() ? '☀️' : '🌙' }}
      </button>
      <button type="button" class="icon-btn" :aria-label="t('nav.lang')" :title="t('nav.lang')" @click="onToggleLocale">
        {{ locale === 'en' ? '中' : 'EN' }}
      </button>
    </div>
  </header>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'
import { isDark, toggleTheme } from '../utils/theme'
import { setLocale, currentLocale } from '../i18n'

const router = useRouter()
const auth = useAuthStore()
const { t, locale } = useI18n()

function handleLogout() {
  auth.logout()
  router.push('/')
}

function onToggleTheme() {
  toggleTheme()
}

function onToggleLocale() {
  setLocale(currentLocale() === 'en' ? 'zh-CN' : 'en')
}
</script>

<style scoped>
.navbar {
  display: flex; justify-content: space-between; align-items: center;
  padding: 14px 40px; background: var(--card-bg);
  box-shadow: 0 2px 8px var(--shadow);
}
.navbar .logo { font-size: 22px; font-weight: bold; color: var(--accent); text-decoration: none; }
.navbar nav a, .navbar nav span { margin-left: 20px; text-decoration: none; color: var(--fg); }
.navbar .user-name { color: var(--accent); font-weight: bold; }
.nav-btn { margin-left: 20px; background: none; border: none; color: var(--fg); font-size: 16px; cursor: pointer; padding: 0; }
.nav-btn:hover { color: var(--accent); }
.nav-actions { display: flex; align-items: center; gap: 8px; }
.icon-btn {
  background: var(--card-bg); border: 1px solid var(--border-strong); border-radius: 6px;
  cursor: pointer; font-size: 15px; width: 34px; height: 34px; line-height: 1;
}
.icon-btn:hover { border-color: var(--accent); }
</style>
