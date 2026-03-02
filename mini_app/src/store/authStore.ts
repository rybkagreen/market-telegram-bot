import { create } from 'zustand'
import type { UserData } from '@/api/auth'

interface AuthState {
  token: string | null
  user: UserData | null
  isAuthenticated: boolean

  setAuth: (token: string, user: UserData) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  // Восстанавливаем из localStorage при перезагрузке
  token: localStorage.getItem('jwt_token'),
  user: (() => {
    try {
      const raw = localStorage.getItem('user_data')
      return raw ? JSON.parse(raw) : null
    } catch {
      return null
    }
  })(),
  isAuthenticated: !!localStorage.getItem('jwt_token'),

  setAuth: (token, user) => {
    localStorage.setItem('jwt_token', token)
    localStorage.setItem('user_data', JSON.stringify(user))
    set({ token, user, isAuthenticated: true })
  },

  logout: () => {
    localStorage.removeItem('jwt_token')
    localStorage.removeItem('user_data')
    set({ token: null, user: null, isAuthenticated: false })
  },
}))
