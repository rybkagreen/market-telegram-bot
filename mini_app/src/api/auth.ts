import { apiClient } from './client'

export interface UserData {
  id: number
  telegram_id: number
  username: string | null
  first_name: string | null
  plan: 'free' | 'starter' | 'pro' | 'business'
  credits: number
  ai_generations_used: number
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: UserData
}

export const authApi = {
  login: (initData: string): Promise<LoginResponse> =>
    apiClient.post('/auth/login', { init_data: initData }).then(r => r.data),

  me: (): Promise<UserData> =>
    apiClient.get('/auth/me').then(r => r.data),
}
