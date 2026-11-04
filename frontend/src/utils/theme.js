// 暗色模式：localStorage 优先，其次跟随系统 prefers-color-scheme
const KEY = 'theme'

export function currentTheme() {
  const saved = localStorage.getItem(KEY)
  if (saved === 'dark' || saved === 'light') return saved
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export function applyTheme(t) {
  document.documentElement.setAttribute('data-theme', t)
}

export function initTheme() {
  applyTheme(currentTheme())
}

export function isDark() {
  return currentTheme() === 'dark'
}

export function toggleTheme() {
  const next = isDark() ? 'light' : 'dark'
  localStorage.setItem(KEY, next)
  applyTheme(next)
  return next
}
