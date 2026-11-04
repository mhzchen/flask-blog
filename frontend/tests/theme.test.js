import { describe, it, expect, beforeEach } from 'vitest'
import { currentTheme, applyTheme, toggleTheme, initTheme } from '../src/utils/theme'

describe('暗色模式 theme', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.removeAttribute('data-theme')
    window.matchMedia = () => ({ matches: false, addListener: () => {}, removeListener: () => {} })
  })

  it('无保存主题时跟随系统 prefers-color-scheme', () => {
    window.matchMedia = () => ({ matches: true })
    expect(currentTheme()).toBe('dark')
    window.matchMedia = () => ({ matches: false })
    expect(currentTheme()).toBe('light')
  })

  it('优先使用已保存的主题', () => {
    localStorage.setItem('theme', 'light')
    expect(currentTheme()).toBe('light')
  })

  it('toggleTheme 切换、持久化并应用到 <html data-theme>', () => {
    localStorage.setItem('theme', 'light')
    const next = toggleTheme()
    expect(next).toBe('dark')
    expect(localStorage.getItem('theme')).toBe('dark')
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
  })

  it('initTheme 应用已保存主题', () => {
    localStorage.setItem('theme', 'dark')
    initTheme()
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
  })

  it('applyTheme 设置指定主题', () => {
    applyTheme('light')
    expect(document.documentElement.getAttribute('data-theme')).toBe('light')
  })
})
