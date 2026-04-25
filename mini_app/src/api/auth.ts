import ky from 'ky'
import type { AuthResponse } from '@/lib/types'
import { api } from '@/api/client'

export interface TicketResponse {
  ticket: string
  portal_url: string
  expires_in: number
}

export function authenticateTelegram(initData: string): Promise<AuthResponse> {
  return ky.post('/api/auth/telegram', { json: { init_data: initData } }).json<AuthResponse>()
}

/**
 * Phase 1 §1.B.3 — bridge ticket exchange.
 *
 * Mints a short-lived (default 300s) ticket-JWT scoped to web_portal. The
 * caller (`OpenInWebPortal`) then opens `${portal_url}/login/ticket?ticket=...`
 * via `Telegram.WebApp.openLink`, where the portal trades it for a real
 * web_portal session.
 */
export function exchangeMiniappToPortal(): Promise<TicketResponse> {
  return api.post('auth/exchange-miniapp-to-portal').json<TicketResponse>()
}
