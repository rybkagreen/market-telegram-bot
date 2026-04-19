import { api } from '@shared/api/client'
import type { User } from '@/lib/types'

export interface LoginResponse {
  access_token: string
  user: User
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
