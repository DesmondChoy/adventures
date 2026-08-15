import { defineConfig, devices } from '@playwright/test';

const runCrossBrowser = process.env.PLAYWRIGHT_CROSS_BROWSER === '1';

export default defineConfig({
  testDir: './tests/playwright',
  timeout: 60_000,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  expect: {
    timeout: 10_000,
    toHaveScreenshot: {
      maxDiffPixelRatio: 0.01,
    },
  },
  use: {
    baseURL: 'http://127.0.0.1:8000',
    headless: true,
    screenshot: 'only-on-failure',
    trace: 'on-first-retry',
    viewport: { width: 1366, height: 900 },
  },
  projects: runCrossBrowser
    ? [
        {
          name: 'chromium-desktop',
          use: { ...devices['Desktop Chrome'] },
        },
        {
          name: 'webkit-mobile',
          use: { ...devices['iPhone 13'] },
        },
      ]
    : undefined,
  webServer: {
    command: '.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000',
    url: 'http://127.0.0.1:8000/select',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
  reporter: process.env.CI
    ? [['list'], ['html', { open: 'never' }]]
    : [['list']],
});
