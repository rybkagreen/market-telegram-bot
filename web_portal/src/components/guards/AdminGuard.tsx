import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { Skeleton } from '@shared/ui'

export default function AdminGuard() {
  const { user, isLoading } = useAuthStore()

  if (isLoading) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-20" />
        <Skeleton className="h-40" />
      </div>
    )
  }

  if (!user?.is_admin) return <Navigate to="/" replace />

  return <Outlet />
}
