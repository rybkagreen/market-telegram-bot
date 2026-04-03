/**
 * AdminGuard — Route guard for admin-only routes
 *
 * Checks `user?.is_admin` via React Query. Non-admin users are
 * immediately redirected to `/` without flashing the admin layout.
 */

import { Navigate, Outlet } from 'react-router-dom'
import { useMe } from '@/hooks/queries'
import { SplashScreen } from '@/components/layout/SplashScreen'

export default function AdminGuard() {
  const { data: user, isLoading } = useMe()

  if (isLoading) return <SplashScreen />

  if (!user?.is_admin) return <Navigate to="/" replace />

  return <Outlet />
}
