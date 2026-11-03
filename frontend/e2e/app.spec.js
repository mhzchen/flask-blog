import { test, expect } from '@playwright/test'

test.describe('博客 E2E', () => {
  test('首页加载并展示文章卡片', async ({ page }) => {
    await page.goto('/')
    const cards = page.locator('.card-link')
    await expect(cards.first()).toBeVisible({ timeout: 30000 })
    expect(await cards.count()).toBeGreaterThan(0)
  })

  test('文章详情：登录后显示浏览量与点赞按钮', async ({ page }) => {
    await page.goto('/login')
    await page.locator('input[type="text"]').fill('runoob')
    await page.locator('input[type="password"]').fill('123456')
    await page.locator('button.btn-submit').click()
    await expect(page).toHaveURL(/\/$/, { timeout: 20000 })
    await page.locator('.card-link').first().click()
    await page.waitForURL(/\/post\//)
    await expect(page.locator('.like-btn')).toBeVisible({ timeout: 30000 })
    await expect(page.locator('body')).toContainText('阅读')
  })

  test('登录后回到首页', async ({ page }) => {
    await page.goto('/login')
    await page.locator('input[type="text"]').fill('runoob')
    await page.locator('input[type="password"]').fill('123456')
    await page.locator('button.btn-submit').click()
    await expect(page).toHaveURL(/localhost:8080\/$/, { timeout: 20000 })
  })
})
