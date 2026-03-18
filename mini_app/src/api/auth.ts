import ky from 'ky'
import type { AuthResponse } from '@/lib/types'

export function authenticateTelegram(initData: string): Promise<AuthResponse> {
  return ky.post('/api/auth/telegram', { json: { init_data: initData } }).json<AuthResponse>()
}
