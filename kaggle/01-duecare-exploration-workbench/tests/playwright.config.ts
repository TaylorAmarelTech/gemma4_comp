import { defineConfig, devices } from '@playwright/test';

const KERNEL_URL = process.env.KERNEL_URL;
if (!KERNEL_URL) {
  console.warn(
    '\n[WARN] KERNEL_URL env var is not set. Tests will fail to connect.\n' +
    '       Set it to your cloudflared trycloudflare.com URL after Run All\n' +
    '       on the kernel 01 Kaggle notebook.\n' +
    '       Example: $env:KERNEL_URL = "https://abc-def-ghi.trycloudflare.com"\n'
  );
}

export default defineConfig({
  testDir: './specs',
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: [
    ['html', { open: 'never' }],
    ['list'],
  ],
  use: {
    baseURL: KERNEL_URL || 'http://localhost:8080',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
    ignoreHTTPSErrors: true,
  },
  projects: [
    {
      name: 'desktop-chromium',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } },
    },
    {
      name: 'tablet',
      testMatch: /visual\.spec\.ts/,
      use: { ...devices['iPad Pro'] },
    },
    {
      name: 'mobile',
      testMatch: /visual\.spec\.ts/,
      use: { ...devices['Pixel 7'] },
    },
  ],
});
