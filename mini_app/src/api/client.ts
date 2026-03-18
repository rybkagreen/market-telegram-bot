// ============================================================
// RekHarbor Mini App — HTTP Client (ky + JWT interceptor)
// Phase 3 | Auto-retry on 401 with fresh Telegram initData
// ============================================================

import ky from 'ky'
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
          console.log('[API Client] Token added to request:', request.url)
        } else {
          console.warn('[API Client] No token found for request:', request.url)
        }
      },
    ],
    afterResponse: [
      async (_request, _options, response) => {
        // ДОБАВЛЕНО (UX-P0): Логирование всех ошибок API
        if (!response.ok) {
          console.error('[API] Error:', response.status, response.url)
          if (response.status === 401) {
            console.log('[API Client] 401 Unauthorized - attempting re-auth...')
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
        return response
      },
    ],
  },
})
