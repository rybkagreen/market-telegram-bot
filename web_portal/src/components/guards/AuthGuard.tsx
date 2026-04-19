import { useEffect, useRef } from 'react'
import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { getMe } from '@/api/auth'

/**
 * AuthGuard — проверяет наличие JWT и валидность через /api/auth/me.
 * Если токен есть в localStorage, но пользователь не загружен — пробуем загрузить.
 */
export function AuthGuard() {
  const { isAuthenticated, isLoading, user, setAuth, setLoading, logout } = useAuthStore()
  const verifiedRef = useRef(false)

  useEffect(() => {
    // Prevent re-verification after initial attempt (avoids loop on logout redirect)
    if (verifiedRef.current) return

    // Нет токена — снять loading, редиректить на /login
    if (!isAuthenticated) {
      setLoading(false)
      return
    }
    // Есть токен и user уже загружен — ничего не делать
    if (user) {
      setLoading(false)
      verifiedRef.current = true
      return
    }
    // Есть токен, нет user — проверить токен через API
    setLoading(true)
    getMe()
      .then((data) => {
        const token = localStorage.getItem('rh_token')
        if (token) {
          setAuth(token, data as Parameters<typeof setAuth>[1])
          verifiedRef.current = true
        } else {
          setLoading(false)
        }
      })
      .catch(() => {
        logout()
        verifiedRef.current = true
      })
  }, [isAuthenticated, user, setAuth, setLoading, logout])

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-harbor-bg">
        <div className="text-center">
          <div className="text-4xl mb-4 animate-pulse">⚓</div>
          <p className="text-text-secondary">Загрузка...</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}
