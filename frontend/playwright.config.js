import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  timeout: 45000,
  fullyParallel: false,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: 'http://localhost:8080',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  // CI 用自带 chromium（npx playwright install chromium）；本地用系统 Edge（无需下载浏览器）
  projects: process.env.CI
    ? [{ name: 'chromium', use: { browserName: 'chromium' } }]
    : [{ name: 'msedge', use: { browserName: 'chromium', channel: 'msedge' } }],
})
