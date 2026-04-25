import { api } from './client'

/**
 * Phase 1 §1.B.2 carve-out — non-PII consent calls.
 *
 * Mirrors `src/api/routers/legal_acceptance.py` on the backend. The URL
 * stays `/api/contracts/accept-rules` for backwards compatibility. This
 * module is the **only** mini_app call site for the endpoint after the
 * legal strip; `mini_app/src/api/contracts.ts` was deleted.
 */
export const legalAcceptanceApi = {
  acceptRules: () =>
    api
      .post('contracts/accept-rules', {
        json: { accept_platform_rules: true, accept_privacy_policy: true },
      })
      .json<{ success: boolean }>(),
}
