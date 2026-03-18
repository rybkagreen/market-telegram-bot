// ============================================================
// RekHarbor Mini App — useAuth hook
// Phase 3 | Telegram initData → JWT auth flow
// ============================================================

import { useEffect } from 'react'
import { useTelegram } from './useTelegram'
import { useAuthStore } from '@/stores/authStore'
import { authenticateTelegram } from '@/api/auth'

export function useAuth() {
  const { initData } = useTelegram()
  const { isAuthenticated, isLoading, user, setAuth, setLoading, logout } = useAuthStore()

  useEffect(() => {
    if (!initData) {
      setLoading(false)
      return
    }

    authenticateTelegram(initData)
      .then(({ access_token, user: authUser }) => {
        setAuth(access_token, authUser)
      })
      .catch(() => {
        logout()
      })
  // run once on mount
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return { isAuthenticated, isLoading, user }
}
