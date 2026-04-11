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

    let cancelled = false
    authenticateTelegram(initData)
      .then(({ access_token, user: authUser }) => {
        if (!cancelled) setAuth(access_token, authUser)
      })
      .catch(() => {
        if (!cancelled) logout()
      })
    return () => { cancelled = true }
  }, [initData, setAuth, logout, setLoading])

  return { isAuthenticated, isLoading, user }
}
