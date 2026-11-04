import { createI18n } from 'vue-i18n'
import zhCN from '../locales/zh-CN'
import en from '../locales/en'

const saved = localStorage.getItem('locale')
const locale = saved === 'en' ? 'en' : 'zh-CN'

const i18n = createI18n({
  legacy: false,
  locale,
  fallbackLocale: 'zh-CN',
  messages: { 'zh-CN': zhCN, en },
})

// 切换语言：写 localStorage + 更新 <html lang>（供 SEO/无障碍）
export function setLocale(l) {
  i18n.global.locale.value = l
  localStorage.setItem('locale', l)
  document.documentElement.lang = l === 'en' ? 'en' : 'zh-CN'
}

export function currentLocale() {
  return i18n.global.locale.value
}

export default i18n
