import { test, expect, request as apiRequest } from '@playwright/test'
import { TEST_USERS } from '../fixtures/roles'

/**
 * Phase 1 §1.B.6b — `ticket-login.spec.ts`.
 *
 * Covers the bridge happy path AND the safeRedirect open-redirect guard:
 *
 *   1. Mint mini_app JWT → exchange → ticket → consume → access_token.
 *      `TicketLogin` screen mounts at `/login/ticket?ticket=...&redirect=/cabinet`,
 *      consumes, persists token, and redirects to `/cabinet`.
 *
 *   2. Open-redirect rejection — `?redirect=https://evil.com` and
 *      `?redirect=//evil.com` must both fall back to `/cabinet`. The
 *      `safeRedirect` allowlist is the security boundary; this spec
 *      locks it in against future regressions.
 *
 * Pre-conditions: same as `legal-profile-requires-web-portal.spec.ts`.
 */

const ADVERTISER = TEST_USERS.advertiser

async function mintTicket(baseURL: string): Promise<string> {
  const ctx = await apiRequest.newContext({ baseURL })

  const login = await ctx.post('/api/auth/e2e-login', {
    data: { telegram_id: ADVERTISER.telegramId, source: 'mini_app' },
  })
  expect(login.ok()).toBeTruthy()
  const { access_token: miniToken } = await login.json()

  const exchange = await ctx.post('/api/auth/exchange-miniapp-to-portal', {
    headers: { Authorization: `Bearer ${miniToken}` },
  })
  expect(exchange.ok(), `exchange failed: ${await exchange.text()}`).toBeTruthy()
  const { ticket } = await exchange.json()

  await ctx.dispose()
  return ticket
}

test.describe('Phase 1 §1.B.3 bridge UI', () => {
  test('happy path: ticket → consume → land on /cabinet', async ({ page, baseURL }) => {
    const ticket = await mintTicket(baseURL!)

    await page.goto(`/login/ticket?ticket=${encodeURIComponent(ticket)}&redirect=/cabinet`)

    // After successful consume the screen redirects (replace) to /cabinet.
    await page.waitForURL(/\/cabinet$/, { timeout: 10_000 })
    expect(await page.evaluate(() => localStorage.getItem('rh_token'))).toBeTruthy()
  })

  test('safeRedirect blocks https://evil.com', async ({ page, baseURL }) => {
    const ticket = await mintTicket(baseURL!)
    const evil = encodeURIComponent('https://evil.com')

    await page.goto(`/login/ticket?ticket=${encodeURIComponent(ticket)}&redirect=${evil}`)

    // Must NOT navigate off-origin; falls back to /cabinet.
    await page.waitForURL(/\/cabinet$/, { timeout: 10_000 })
    expect(page.url()).not.toContain('evil.com')
  })

  test('safeRedirect blocks //evil.com (protocol-relative)', async ({ page, baseURL }) => {
    const ticket = await mintTicket(baseURL!)
    const evil = encodeURIComponent('//evil.com')

    await page.goto(`/login/ticket?ticket=${encodeURIComponent(ticket)}&redirect=${evil}`)

    await page.waitForURL(/\/cabinet$/, { timeout: 10_000 })
    expect(page.url()).not.toContain('evil.com')
  })
})
