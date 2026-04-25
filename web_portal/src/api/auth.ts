import { api } from '@shared/api/client'
import type { User } from '@/lib/types'

export interface LoginResponse {
  access_token: string
  user: User
}

export interface AuthTokenResponse {
  access_token: string
  token_type: 'bearer'
  source: 'mini_app' | 'web_portal'
}

export async function loginWidget(data: Record<string, unknown>) {
  return api.post('auth/telegram-login-widget', { json: data }).json<LoginResponse>()
}

export async function loginByCode(code: string) {
  return api.post('auth/login-code', { json: { code } }).json<LoginResponse>()
}

export async function getMe() {
  return api.get('auth/me').json<User>()
}

/**
 * Phase 1 §1.B.3 — bridge consume.
 *
 * Mini_app issues a short-lived ticket via /api/auth/exchange-miniapp-to-portal;
 * the portal trades it for a long-lived web_portal JWT here. The endpoint is
 * one-shot: replays return 401 (jti is deleted on first consume).
 */
export async function consumeTicket(ticket: string) {
  return api.post('auth/consume-ticket', { json: { ticket } }).json<AuthTokenResponse>()
}
