import { defineConfig, devices } from '@playwright/test'

const BASE_URL = process.env.BASE_URL ?? 'http://nginx-test'

export default defineConfig({
  testDir: './specs',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [
    ['list'],
    ['html', { outputFolder: '/e2e/reports/html', open: 'never' }],
    ['json', { outputFile: '/e2e/reports/results.json' }],
  ],
  outputDir: '/e2e/reports/artifacts',
  use: {
    baseURL: BASE_URL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    ignoreHTTPSErrors: true,
  },
  expect: {
    timeout: 10_000,
    toHaveScreenshot: {
      // Per-pixel RGB tolerance 0..1 — small values absorb anti-aliasing
      // differences that are invisible but measurable.
      threshold: 0.2,
      // Total % of pixels that may differ without failing the test. At
      // 0.5% a full-page 1440×900 screenshot tolerates ~6500 pixels.
      maxDiffPixelRatio: 0.005,
      animations: 'disabled',
    },
  },

  snapshotDir: './visual-snapshots',
  snapshotPathTemplate:
    '{snapshotDir}/{testFileDir}/{testFileName}-snapshots/{arg}-{projectName}{ext}',

  globalSetup: './global-setup.ts',

  projects: [
    { name: 'mobile-webkit', use: { ...devices['iPhone SE'] } },
    { name: 'mobile-chromium', use: { ...devices['Pixel 5'] } },
    {
      name: 'desktop-chromium',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1440, height: 900 },
      },
    },
  ],
})
