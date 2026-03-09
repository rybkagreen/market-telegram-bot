import { useState, useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { BottomNav } from '@/components/layout/BottomNav'
import Auth from '@/pages/Auth'
import Dashboard from '@/pages/Dashboard'
import Campaigns from '@/pages/Campaigns'
import Analytics from '@/pages/Analytics'
import Channels from '@/pages/Channels'
import Billing from '@/pages/Billing'
import Comparison from '@/pages/Comparison'
import { PlatformStats } from '@/pages/PlatformStats'

export default function App() {
  const { isAuthenticated } = useAuthStore()
  const [authed, setAuthed] = useState(isAuthenticated)

  useEffect(() => {
    const tg = window.Telegram?.WebApp
    if (!tg) return
    document.documentElement.setAttribute('data-theme', tg.colorScheme ?? 'dark')
    tg.onEvent('themeChanged', () => {
      document.documentElement.setAttribute('data-theme', tg.colorScheme)
    })
  }, [])

  if (!authed) {
    return <Auth onSuccess={() => setAuthed(true)} />
  }

  return (
    <div className="app-shell">
      <Routes>
        <Route path="/"           element={<Dashboard />} />
        <Route path="/campaigns"  element={<Campaigns />} />
        <Route path="/analytics"  element={<Analytics />} />
        <Route path="/channels"   element={<Channels />} />
        <Route path="/comparison" element={<Comparison />} />
        <Route path="/billing"    element={<Billing />}   />
        <Route path="/stats"      element={<PlatformStats />} />
        <Route path="*"           element={<Navigate to="/" />} />
      </Routes>
      <BottomNav />
    </div>
  )
}
