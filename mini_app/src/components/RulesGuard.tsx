import { useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useMe } from '@/hooks/queries/useUserQueries'

const EXEMPT_ROUTES = ['/accept-rules', '/legal-profile-prompt', '/legal-profile']

export function RulesGuard({ children }: { children: React.ReactNode }) {
  const { data: user } = useMe()
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    if (!user) return
    const needsRules = !user.platform_rules_accepted_at || !user.privacy_policy_accepted_at
    const isExempt = EXEMPT_ROUTES.some((r) => location.pathname.startsWith(r))
    if (needsRules && !isExempt) {
      navigate('/accept-rules', { replace: true })
    }
  }, [user, location.pathname, navigate])

  return <>{children}</>
}
