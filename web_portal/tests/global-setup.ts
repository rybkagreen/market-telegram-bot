import { request } from '@playwright/test'
import { mkdir, writeFile } from 'node:fs/promises'
import { dirname } from 'node:path'
import { TEST_USERS } from './fixtures/roles'

/**
 * Global setup — runs once before the suite.
 *
 * For each seeded role, call the test-only /api/auth/e2e-login endpoint,
 * capture the JWT, and build a storageState file so individual specs can
 * load pre-authenticated contexts without re-logging-in.
 *
 * The endpoint only exists when api-test has ENVIRONMENT=testing (see
 * src/api/main.py) — it 404s in any other environment.
 */
export default async function globalSetup() {
  const baseURL = process.env.BASE_URL ?? 'http://nginx-test'
  const apiContext = await request.newContext({ baseURL })

  for (const [role, cfg] of Object.entries(TEST_USERS)) {
    const resp = await apiContext.post('/api/auth/e2e-login', {
      // source=web_portal: storageState tokens used by request fixture must
      // satisfy the strictest audience dep (`get_current_user_from_web_portal`).
      // Generic `get_current_user` also accepts web_portal — no regression on
      // mini_app-style endpoints. Specs needing mini_app aud (ticket-login,
      // legal-profile-requires-web-portal) mint their own tokens explicitly.
      data: { telegram_id: cfg.telegramId, source: 'web_portal' },
    })
    if (!resp.ok()) {
      const body = await resp.text()
      throw new Error(
        `[global-setup] e2e-login failed for role=${role}: ${resp.status()} ${body}`,
      )
    }
    const { access_token, user } = await resp.json()

    const origin = new URL(baseURL).origin
    const storageState = {
      cookies: [],
      origins: [
        {
          origin,
          localStorage: [
            { name: 'rh_token', value: access_token },
            { name: 'rh_user', value: JSON.stringify(user) },
          ],
        },
      ],
    }

    await mkdir(dirname(cfg.storageFile), { recursive: true })
    await writeFile(cfg.storageFile, JSON.stringify(storageState, null, 2))
    console.log(`[global-setup] role=${role} storage → ${cfg.storageFile}`)
  }

  await apiContext.dispose()
}
