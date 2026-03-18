// ============================================================
// RekHarbor Mini App — useBackButton hook
// Phase 3 | Telegram BackButton ↔ React Router navigation
// ============================================================

import { useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'

export function useBackButton() {
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    const tg = window.Telegram?.WebApp
    if (!tg) return

    const handleBack = () => navigate(-1)

    if (location.pathname === '/') {
      tg.BackButton.hide()
    } else {
      tg.BackButton.show()
      tg.BackButton.onClick(handleBack)
    }

    return () => {
      tg.BackButton.offClick(handleBack)
    }
  }, [location.pathname, navigate])
}
