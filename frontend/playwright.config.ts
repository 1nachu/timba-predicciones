import { defineConfig, devices } from '@playwright/test';

const pythonCmd =
  process.platform === 'win32'
    ? '..\\.venv\\Scripts\\python.exe ../app.py'
    : 'python ../app.py';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: 'list',
  use: {
    baseURL: 'http://127.0.0.1:3000',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium-desktop',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'mobile-pixel7',
      use: { ...devices['Pixel 7'] },
    },
  ],
  webServer: [
    {
      command: pythonCmd,
      url: 'http://127.0.0.1:5000/api/v1/health',
      reuseExistingServer: !process.env.CI,
      timeout: 60000,
      env: {
        E2E_SEED_DATA: '1',
      },
    },
    {
      command: 'npm run start',
      url: 'http://127.0.0.1:3000',
      reuseExistingServer: !process.env.CI,
      timeout: 60000,
      env: {
        API_INTERNAL_URL: 'http://127.0.0.1:5000',
      },
    },
  ],
});
