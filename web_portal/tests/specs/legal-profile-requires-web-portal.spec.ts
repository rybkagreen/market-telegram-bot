import { test, expect, request as apiRequest } from '@playwright/test'
import { TEST_USERS } from '../fixtures/roles'

/**
 * Phase 1 §1.B.6b — `legal-profile-requires-web-portal.spec.ts`.
 *
 * Verifies the FZ-152 backend guard (§1.B.1):
 *   1. mini_app JWT → 403 on /api/legal-profile/me (negative path).
 *   2. web_portal JWT → 200 on /api/legal-profile/me (positive path).
 *
 * Both branches mint their JWT directly via /api/auth/e2e-login (Phase 1
 * §1.B.6a added the `source` parameter). The spec runs on all three
 * viewport projects; assertions are HTTP-level (not visual) so the
 * viewport matrix exercises the request flow uniformly.
 *
 * Pre-conditions (documented in tests/integration/README.md):
 *   - docker-compose.test.yml stack up
 *   - scripts/e2e/seed_e2e.py executed (advertiser at telegram_id=9001)
 *   - ENABLE_E2E_AUTH=true in api container
 */

const ADVERTISER = TEST_USERS.advertiser

test.describe('FZ-152 web_portal-only guard on /api/legal-profile/me', () => {
  test('mini_app JWT → 403', async ({ baseURL }) => {
    const ctx = await apiRequest.newContext({ baseURL })
    const minted = await ctx.post('/api/auth/e2e-login', {
      data: { telegram_id: ADVERTISER.telegramId, source: 'mini_app' },
    })
    expect(minted.ok(), `e2e-login failed: ${await minted.text()}`).toBeTruthy()
    const { access_token } = await minted.json()

    const resp = await ctx.get('/api/legal-profile/me', {
      headers: { Authorization: `Bearer ${access_token}` },
    })
    expect(resp.status(), 'mini_app aud must be rejected with 403').toBe(403)

    await ctx.dispose()
  })

  test('web_portal JWT → 200', async ({ baseURL }) => {
    const ctx = await apiRequest.newContext({ baseURL })
    const minted = await ctx.post('/api/auth/e2e-login', {
      data: { telegram_id: ADVERTISER.telegramId, source: 'web_portal' },
    })
    expect(minted.ok(), `e2e-login failed: ${await minted.text()}`).toBeTruthy()
    const { access_token, source } = await minted.json()
    expect(source).toBe('web_portal')

    const resp = await ctx.get('/api/legal-profile/me', {
      headers: { Authorization: `Bearer ${access_token}` },
    })
    expect(resp.status(), 'web_portal aud must be accepted').toBe(200)

    await ctx.dispose()
  })
})
