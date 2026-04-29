import { useEffect, useRef } from 'react'
import { useNavigate, useLocation, Outlet } from 'react-router-dom'
import { useNeedsAcceptRules } from '@/hooks/useUserQueries'

const EXEMPT_ROUTES = ['/accept-rules', '/legal-profile-prompt', '/legal-profile']

export function RulesGuard() {
  const { data, isLoading, isRefetching } = useNeedsAcceptRules()
  const navigate = useNavigate()
  const location = useLocation()
  const hasRedirected = useRef(false)

  useEffect(() => {
    if (isLoading || !data || isRefetching) return
    const isExempt = EXEMPT_ROUTES.some((r) => location.pathname.startsWith(r))
    if (data.needs_accept && !isExempt && !hasRedirected.current) {
      hasRedirected.current = true
      navigate('/accept-rules', { replace: true })
    }
  }, [data, isLoading, isRefetching, location.pathname, navigate])

  if (isLoading) return null

  return <Outlet />
}
