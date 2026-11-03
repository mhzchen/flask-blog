import { test, expect } from '@playwright/test'

// 唯一时间戳，避免多次运行残留数据冲突
const T = Date.now()

async function login(page) {
  await page.goto('/login')
  await page.locator('input[type="text"]').fill('runoob')
  await page.locator('input[type="password"]').fill('123456')
  await page.locator('button.btn-submit').click()
  await expect(page).toHaveURL(/\/$/, { timeout: 20000 })
}

test.describe('博客真实链路 E2E', () => {
  test('搜索：关键词过滤文章列表', async ({ page }) => {
    await page.goto('/')
    await page.locator('input.search-input').fill('Flask')
    await page.locator('button.btn-submit').click()
    await expect(page.locator('.card-link').first()).toBeVisible({ timeout: 30000 })
    // 结果区出现"篇文章"统计
    await expect(page.locator('body')).toContainText('篇文章', { timeout: 20000 })
  })

  test('发帖：登录 → 新建文章 → 首页可见', async ({ page }) => {
    const title = `E2E 发帖 ${T}`
    await login(page)
    await page.goto('/admin')
    await page.locator('button.btn-add').click()
    // 发帖 modal：标题(input.form-input 第1个) + 内容(textarea.form-input)
    await page.locator('input.form-input').nth(0).fill(title)
    await page.locator('textarea.form-input').fill(`E2E 测试内容 ${T}`)
    await page.locator('button.btn-sm.primary').click()
    // 保存后列表出现新文章标题
    await expect(page.locator('body')).toContainText(title, { timeout: 20000 })
    // 回首页搜索该标题 → 结果可见（发帖已持久化）
    await page.goto('/')
    await page.locator('input.search-input').fill(title)
    await page.locator('button.btn-submit').click()
    await expect(page.locator('body')).toContainText(title, { timeout: 20000 })
  })

  test('评论：登录 → 打开文章 → 发表评论 → 可见', async ({ page }) => {
    await login(page)
    await page.locator('.card-link').first().click()
    await page.waitForURL(/\/post\//)
    const c = `E2E 评论 ${T}`
    await page.locator('textarea[placeholder="写下你的评论..."]').fill(c)
    await page.locator('button', { hasText: '发表评论' }).click()
    await expect(page.locator('body')).toContainText(c, { timeout: 20000 })
  })
})