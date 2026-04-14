// ============================================================
// RekHarbor Mini App — HTTP Client (ky + JWT interceptor)
// Phase 3 | Auto-retry on 401 with fresh Telegram initData
// ============================================================

import ky from 'ky'
import * as Sentry from '@sentry/react'
import type { AuthResponse } from '@/lib/types'
import { useAuthStore } from '@/stores/authStore'

export const api = ky.create({
  prefixUrl: '/api',
  timeout: 15_000,
  hooks: {
    beforeRequest: [
      (request) => {
        const token = useAuthStore.getState().token
        if (token) {
          request.headers.set('Authorization', `Bearer ${token}`)
        }
      },
    ],
    afterResponse: [
      async (_request, _options, response) => {
        // ДОБАВЛЕНО (UX-P0): Логирование всех ошибок API
        if (!response.ok) {
          Sentry.captureException(new Error(`[API] Error: ${response.status} ${response.url}`))
          if (response.status === 401) {
            Sentry.addBreadcrumb({ message: '[API Client] 401 Unauthorized - attempting re-auth...', level: 'info' })
          }
        }
        if (response.status === 401) {
          const tg = window.Telegram?.WebApp
          if (tg?.initData) {
            try {
              const res = await ky
                .post('/api/auth/telegram', { json: { init_data: tg.initData } })
                .json<AuthResponse>()
              useAuthStore.getState().setAuth(res.access_token, res.user)
            } catch {
              useAuthStore.getState().logout()
            }
          }
        }
        // 403 structured error for legal_profile_* codes
        if (response.status === 403) {
          try {
            const body = await response.clone().json() as {
              detail?: { code?: string; message?: string; redirect?: string }
            }
            if (body?.detail?.code?.startsWith('legal_profile_')) {
              const err = new Error(body.detail.code) as Error & {
                detail: typeof body.detail
              }
              err.detail = body.detail
              throw err
            }
          } catch (parseErr) {
            if ((parseErr as Error)?.detail) throw parseErr
            // SyntaxError on JSON parse — ignore, let caller handle generic 403
          }
        }
        return response
      },
    ],
  },
})
