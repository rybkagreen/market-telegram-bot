import { create } from 'zustand'

interface User {
  id: number
  telegram_id: number
  username: string | null
  first_name: string
  last_name: string | null
  plan: string
  role: string
  balance_rub: string
  earned_rub: string
  credits: number
  is_admin: boolean
}

interface AuthState {
  token: string | null
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  setAuth: (token: string, user: User) => void
  logout: () => void
  setLoading: (loading: boolean) => void
}

export const useAuthStore = create<AuthState>()((set) => ({
  token: typeof window !== 'undefined' ? localStorage.getItem('rh_token') : null,
  user: null,
  isAuthenticated: !!localStorage.getItem('rh_token'),
  isLoading: !!localStorage.getItem('rh_token'),

  setAuth: (token, user) => {
    localStorage.setItem('rh_token', token)
    localStorage.setItem('rh_user', JSON.stringify(user))
    set({ token, user, isAuthenticated: true, isLoading: false })
  },

  logout: () => {
    localStorage.removeItem('rh_token')
    localStorage.removeItem('rh_user')
    set({ token: null, user: null, isAuthenticated: false, isLoading: false })
  },

  setLoading: (loading) => set({ isLoading: loading }),
}))
