import { test, expect } from '../fixtures/test'
import { TEST_USERS } from '../fixtures/roles'

/**
 * Phase 4 — Supplementary Agreement (ДС) signing flow.
 *
 * Smoke coverage that verifies:
 *   1. GET /api/placements/{id}/supplementary-agreements endpoint reachable
 *      and returns a sensible status (200 / 403 / 404 — never 500).
 *   2. SupplementaryAgreementSection component imports cleanly on both
 *      CampaignWaiting (advertiser) and OwnRequestDetail (owner) screens —
 *      verified across 3 viewports (mobile-webkit, mobile-chromium,
 *      desktop-chromium per playwright.config.ts projects).
 *
 * Full two-session sign round-trip (advertiser signs → owner signs →
 * placement progresses) requires a seed fixture for a placement in
 * pending_owner with already-generated ДС pair AND both framework
 * contracts signed for advertiser+owner. Current scripts/e2e/seed_e2e.py
 * does not produce this state — see BL-001/BL-002 pattern in CLAUDE.md
 * for the analogous escrow/bot-API blockers. When that fixture lands,
 * promote the smoke checks below into a full interactive test.
 */

const advertiser = TEST_USERS.advertiser
const owner = TEST_USERS.owner

// ─── 1. API endpoint contract ────────────────────────────────────────

test.describe('[flow] supplementary agreement API endpoint', () => {
  test.use({ storageState: advertiser.storageFile })

  test('GET /api/placements/{id}/supplementary-agreements never 500s', async ({
    request,
  }) => {
    // Probe with a placement id that almost certainly doesn't exist for the
    // test user. Endpoint must respond with 404 (placement missing) or 403
    // (non-participant); a 500 would indicate a wiring regression.
    const resp = await request.get('/api/placements/999999999/supplementary-agreements')
    expect(
      [200, 403, 404].includes(resp.status()),
      `unexpected status ${resp.status()} — body: ${await resp.text()}`,
    ).toBeTruthy()
  })

  test('endpoint returns JSON content-type when reachable', async ({ request }) => {
    const resp = await request.get('/api/placements/999999999/supplementary-agreements')
    const ct = resp.headers()['content-type'] ?? ''
    expect(ct.startsWith('application/json'), `content-type was ${ct}`).toBeTruthy()
  })
})

// ─── 2. CampaignWaiting renders without crash (advertiser side) ──────

test.describe('[flow] CampaignWaiting renders ДС-aware', () => {
  test.use({ storageState: advertiser.storageFile })

  test('navigates to /adv/campaigns/{id} for active placement without 500', async ({
    page,
  }) => {
    const errors: string[] = []
    page.on('pageerror', (err) => errors.push(`pageerror: ${err.message}`))
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(`console.error: ${msg.text()}`)
    })

    // First find a placement id the advertiser has (any status)
    const listResp = await page.request.get('/api/placements/?view=advertiser&limit=1')
    if (!listResp.ok()) {
      test.skip(true, 'no placements available — seed required')
    }
    const list = (await listResp.json()) as { id: number; status: string }[]
    if (list.length === 0) {
      test.skip(true, 'no placements available — seed required')
    }
    const placementId = list[0].id

    const resp = await page.goto(`/adv/campaigns/${placementId}`, {
      waitUntil: 'networkidle',
    })
    expect(resp?.ok(), `HTTP for /adv/campaigns/${placementId}`).toBeTruthy()

    // SupplementaryAgreementSection conditionally renders only when status is
    // pending_owner|counter_offer. We don't require it to be visible — we just
    // assert no crash from the component's mere presence on the bundle.
    expect(errors, errors.join('\n')).toHaveLength(0)
  })
})

// ─── 3. OwnRequestDetail renders without crash (owner side) ──────────

test.describe('[flow] OwnRequestDetail renders ДС-aware', () => {
  test.use({ storageState: owner.storageFile })

  test('navigates to /own/requests/{id} without 500', async ({ page }) => {
    const errors: string[] = []
    page.on('pageerror', (err) => errors.push(`pageerror: ${err.message}`))
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(`console.error: ${msg.text()}`)
    })

    const listResp = await page.request.get('/api/placements/?view=owner&limit=1')
    if (!listResp.ok()) {
      test.skip(true, 'no placements available — seed required')
    }
    const list = (await listResp.json()) as { id: number; status: string }[]
    if (list.length === 0) {
      test.skip(true, 'no placements available — seed required')
    }
    const placementId = list[0].id

    const resp = await page.goto(`/own/requests/${placementId}`, {
      waitUntil: 'networkidle',
    })
    expect(resp?.ok(), `HTTP for /own/requests/${placementId}`).toBeTruthy()
    expect(errors, errors.join('\n')).toHaveLength(0)
  })
})
