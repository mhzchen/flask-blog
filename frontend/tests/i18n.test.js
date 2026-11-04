import { describe, it, expect } from 'vitest'
import i18n, { setLocale, currentLocale } from '../src/i18n'

describe('i18n 国际化', () => {
  it('zh-CN 默认文案', () => {
    setLocale('zh-CN')
    expect(i18n.global.t('nav.home')).toBe('首页')
    expect(i18n.global.t('auth.login')).toBe('登录')
  })

  it('切换到 en 文案变化', () => {
    setLocale('en')
    expect(i18n.global.t('nav.home')).toBe('Home')
    expect(i18n.global.t('auth.login')).toBe('Login')
  })

  it('currentLocale 返回当前语言', () => {
    setLocale('en')
    expect(currentLocale()).toBe('en')
    setLocale('zh-CN')
    expect(currentLocale()).toBe('zh-CN')
  })

  it('带插值参数的消息', () => {
    setLocale('zh-CN')
    expect(i18n.global.t('post.views', { n: 42 })).toBe('42 阅读')
  })
})
