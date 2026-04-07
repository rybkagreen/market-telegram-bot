import ky from 'ky'
import type { AuthResponse } from '@/lib/types'

export function authenticateTelegram(initData: string): Promise<AuthResponse> {
  return ky.post('/api/auth/telegram', { json: { init_data: initData } }).json<AuthResponse>()
}

export function authenticateLoginWidget(data: Record<string, unknown>): Promise<AuthResponse> {
  return ky.post('/api/auth/telegram-login-widget', { json: data }).json<AuthResponse>()
}

export async function getMe() {
  return ky.get('/api/auth/me').json<AuthResponse['user']>()
}
