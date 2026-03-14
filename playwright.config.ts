import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,          // Run sequentially to avoid state bleed
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,                    // Single worker for sequential execution
  reporter: 'html',
  timeout: 30_000,

  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  /* Start both backend and frontend dev servers before running tests */
  webServer: [
    {
      command: 'cd backend && source venv/bin/activate && uvicorn app.main:app --port 8000',
      url: 'http://localhost:8000/health',
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
    },
    {
      command: 'cd frontend && npm run dev',
      url: 'http://localhost:5173',
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
    },
  ],

  projects: [
    {
      name: 'global-setup',
      testMatch: /global-setup\.ts/,
    },
    {
      name: 'smoke',
      testMatch: /smoke\.spec\.ts/,
      dependencies: ['global-setup'],
    },
  ],
});
