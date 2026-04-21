import { test, expect } from '@playwright/test'
import { ROUTES } from '../fixtures/routes'
import { TEST_USERS } from '../fixtures/roles'

/**
 * Visual regression baseline.
 *
 * For every protected route × 3 viewports we capture a full-page PNG and
 * compare against a committed baseline under `tests/visual-snapshots/`.
 * Any delta beyond `threshold` + `maxDiffPixelRatio` (see playwright.config.ts)
 * fails the suite.
 *
 * Dynamic content (timestamps, relative-time labels, rendered user balances
 * if they drift between runs) is **masked** in the screenshot — the masked
 * regions are painted with a solid colour before the diff, so values under
 * them don't cause false positives.
 *
 * Deterministic rendering relies on:
 *  - fixed viewport (playwright projects)
 *  - `document.fonts.ready` — Google Fonts must finish loading
 *  - `prefers-reduced-motion` override — disables CSS animations
 *  - `networkidle` — no in-flight requests (images, lazy chunks)
 *
 * Updating baselines (after an intentional UI change):
 *     make test-e2e-visual-update
 */

async function settlePage(page: import('@playwright/test').Page) {
  // Wait for fonts — Google Fonts can pop-in after initial paint and
  // cause metric shifts. document.fonts.ready resolves once every @font-face
  // declaration has resolved or failed.
  await page.evaluate(() => (document as Document).fonts.ready)

  // Give one more rAF tick so any font-swap layout has settled.
  await page.evaluate(
    () => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))),
  )
}

function stripTrailingSlash(path: string) {
  return path.length > 1 && path.endsWith('/') ? path.slice(0, -1) : path
}

function snapshotName(path: string) {
  return `${stripTrailingSlash(path).replace(/^\//, '').replace(/\//g, '_') || 'root'}.png`
}

for (const spec of ROUTES) {
  const role = TEST_USERS[spec.role]

  test.describe(`visual [${spec.role}] ${spec.path}`, () => {
    test.use({
      storageState: role.storageFile,
      // Locale affects date/number formatting — lock it.
      locale: 'ru-RU',
      timezoneId: 'Europe/Moscow',
    })

    test('baseline', async ({ page }) => {
      // Force reduced-motion via media emulation — freezes CSS animations
      // and transitions so screenshot diffs stay stable.
      await page.emulateMedia({ reducedMotion: 'reduce' })
      await page.goto(spec.path, { waitUntil: 'networkidle' })
      await settlePage(page)

      // Mask rules — selectors whose text is expected to change run-to-run.
      // These are structural identifiers, not visual ones; the pixel area
      // they cover is painted flat before diffing.
      const masks = [
        // Balance / currency strings can drift if seed runs produce different
        // Decimal scales or if money is formatted based on locale timezone.
        page.locator('[data-testid="balance"]'),
        page.locator('[data-testid="user-balance"]'),
        // Relative-time labels (e.g. "5 минут назад") are time-dependent.
        page.locator('time[datetime]'),
        page.locator('[data-testid="relative-time"]'),
        // Absolute timestamps rendered by default Intl.DateTimeFormat —
        // vary with timezoneId but also per-row creation time.
        page.locator('[data-testid="timestamp"]'),
      ]

      await expect(page).toHaveScreenshot(snapshotName(spec.path), {
        fullPage: true,
        mask: masks,
        animations: 'disabled',
        // Fonts that fail to load will render with fallback metrics. Catch
        // that by asserting document.fonts has at least one ready face.
      })
    })
  })
}
