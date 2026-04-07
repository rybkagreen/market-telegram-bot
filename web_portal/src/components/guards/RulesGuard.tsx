import { useEffect, useRef } from 'react'
import { useNavigate, useLocation, Outlet } from 'react-router-dom'
import { useMe } from '@/hooks/queries'

const EXEMPT_ROUTES = ['/accept-rules', '/legal-profile-prompt', '/legal-profile']

export function RulesGuard() {
  const { data: user, isLoading, isRefetching } = useMe()
  const navigate = useNavigate()
  const location = useLocation()
  const hasRedirected = useRef(false)

  useEffect(() => {
    if (isLoading || !user || isRefetching) return
    const needsRules = !user.platform_rules_accepted_at || !user.privacy_policy_accepted_at
    const isExempt = EXEMPT_ROUTES.some((r) => location.pathname.startsWith(r))
    if (needsRules && !isExempt && !hasRedirected.current) {
      hasRedirected.current = true
      navigate('/accept-rules', { replace: true })
    }
  }, [user, isLoading, isRefetching, location.pathname, navigate])

  // While checking, show nothing (prevent flash of PortalShell)
  if (isLoading) return null

  return <Outlet />
}
