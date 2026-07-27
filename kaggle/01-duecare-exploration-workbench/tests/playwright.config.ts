import { defineConfig, devices } from '@playwright/test';
import { existsSync } from 'node:fs';
import { resolve } from 'node:path';

const KERNEL_URL = process.env.KERNEL_URL;
const LOCAL_URL = 'http://127.0.0.1:8811';
const repoPython = resolve(
  __dirname,
  process.platform === 'win32'
    ? '../../../.venv/Scripts/python.exe'
    : '../../../.venv/bin/python',
);
const testPython = process.env.DUECARE_TEST_PYTHON ||
  (existsSync(repoPython) ? `"${repoPython}"` : 'python');
const executablePath = process.env.PLAYWRIGHT_EXECUTABLE_PATH;

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
    baseURL: KERNEL_URL || LOCAL_URL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
    ignoreHTTPSErrors: true,
    launchOptions: executablePath ? { executablePath } : undefined,
  },
  webServer: KERNEL_URL ? undefined : {
    command: `${testPython} local_fake_workbench.py`,
    url: `${LOCAL_URL}/api/health`,
    reuseExistingServer: true,
    timeout: 120_000,
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
