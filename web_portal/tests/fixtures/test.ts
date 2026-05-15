import { test as base, expect, request, type APIRequestContext } from '@playwright/test'
import { readFileSync } from 'node:fs'

/**
 * Custom `test` fixture that propagates the auth token from a spec's
 * configured `storageState` into the Playwright `request` fixture.
 *
 * Background: `web_portal/tests/global-setup.ts` writes JWT to
 * localStorage (`rh_token`) — not cookies — because the production
 * frontend uses Authorization-header auth. The browser context loads
 * localStorage when a spec sets `test.use({ storageState })`, so
 * `page`-driven flows authenticate naturally. But the `request` fixture
 * is a separate `APIRequestContext` that does NOT execute JS and only
 * inherits cookies; specs calling `request.post(...)` after
 * `test.use({ storageState })` therefore ship no Authorization header
 * and the API responds 401 "Authorization header missing".
 *
 * This module overrides the `request` fixture: it reads the merged
 * `storageState` (built-in fixture, returns the path or object passed
 * via `test.use({ storageState })`), extracts `rh_token` from the
 * localStorage block, and creates the request context with
 * `extraHTTPHeaders: { Authorization: 'Bearer …' }`. Specs not using
 * storageState see `storageState === undefined` and get an unauthed
 * context — same behavior as the base fixture.
 *
 * Specs that mint their own tokens via `apiRequest.newContext(...)`
 * (e.g. legal-profile-requires-web-portal.spec.ts, ticket-login.spec.ts)
 * bypass this fixture entirely; they continue to work unchanged.
 *
 * For specs that need to call the API as multiple roles in a single
 * test (deep-flows.spec.ts placement lifecycle, payouts visibility):
 * use `apiRequestFor(storageStateFile)` — returns an `APIRequestContext`
 * authed against the JWT in the given storageState. Contexts are
 * auto-disposed at test teardown.
 */

function bearerFromStorageState(state: unknown): string | undefined {
  if (!state || typeof state !== 'string') return undefined
  try {
    const parsed = JSON.parse(readFileSync(state, 'utf-8')) as {
      origins?: Array<{ localStorage?: Array<{ name: string; value: string }> }>
    }
    const ls = parsed.origins?.[0]?.localStorage ?? []
    const token = ls.find((kv) => kv.name === 'rh_token')?.value
    return token ? `Bearer ${token}` : undefined
  } catch {
    return undefined
  }
}

type ApiRequestForRole = (storageStateFile: string) => Promise<APIRequestContext>

export const test = base.extend<{ apiRequestFor: ApiRequestForRole }>({
  request: async ({ playwright, baseURL, storageState }, use) => {
    const auth = bearerFromStorageState(storageState)
    const ctx = await playwright.request.newContext({
      baseURL,
      extraHTTPHeaders: auth ? { Authorization: auth } : undefined,
    })
    await use(ctx)
    await ctx.dispose()
  },
  apiRequestFor: async ({ playwright, baseURL }, use) => {
    const created: APIRequestContext[] = []
    const factory: ApiRequestForRole = async (storageStateFile) => {
      const auth = bearerFromStorageState(storageStateFile)
      const ctx = await playwright.request.newContext({
        baseURL,
        extraHTTPHeaders: auth ? { Authorization: auth } : undefined,
      })
      created.push(ctx)
      return ctx
    }
    await use(factory)
    for (const ctx of created) await ctx.dispose()
  },
})

export { expect, request }
