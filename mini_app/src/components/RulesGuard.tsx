import { useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useNeedsAcceptRules } from '@/hooks/queries/useUserQueries'

const EXEMPT_ROUTES = ['/accept-rules', '/legal-profile-prompt', '/legal-profile']

export function RulesGuard({ children }: { children: React.ReactNode }) {
  const { data, isLoading } = useNeedsAcceptRules()
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    if (isLoading || !data) return
    const isExempt = EXEMPT_ROUTES.some((r) => location.pathname.startsWith(r))
    if (data.needs_accept && !isExempt) {
      navigate('/accept-rules', { replace: true })
    }
  }, [data, isLoading, location.pathname, navigate])

  return <>{children}</>
}
