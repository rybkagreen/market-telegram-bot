import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ScreenHeader, Skeleton, Notification } from '@shared/ui'
import { useMe } from '@/hooks/queries'
import {
  useAdvertiserAnalytics,
  useOwnerAnalytics,
} from '@/hooks/useAnalyticsQueries'
import { useMyChannels } from '@/hooks/useChannelQueries'
import { AIInsightCard } from './analytics/AIInsightCard'
import { ChannelDeepDive } from './analytics/ChannelDeepDive'
import { TrendComparison } from './analytics/TrendComparison'
import { RoleTabs } from './analytics/RoleTabs'
import type { InsightsRole } from '@/api/analytics'

export default function Analytics() {
  const { data: user, isLoading: userLoading, isError: userError } = useMe()
  const { data: advData } = useAdvertiserAnalytics()
  const { data: ownerData } = useOwnerAnalytics()
  const { data: myChannels } = useMyChannels()

  const hasAdvertiserActivity = (advData?.total_campaigns ?? 0) > 0
  const hasOwnerActivity =
    (ownerData?.channel_count ?? 0) > 0 || (myChannels?.length ?? 0) > 0

  const showTabs = hasAdvertiserActivity && hasOwnerActivity
  const defaultRole: InsightsRole = hasOwnerActivity && !hasAdvertiserActivity
    ? 'owner'
    : 'advertiser'

  const [searchParams, setSearchParams] = useSearchParams()
  const paramRole = searchParams.get('role')
  const initialRole: InsightsRole =
    paramRole === 'owner' || paramRole === 'advertiser'
      ? (paramRole as InsightsRole)
      : defaultRole

  const [role, setRole] = useState<InsightsRole>(initialRole)

  // Keep URL in sync when user flips tabs
  useEffect(() => {
    if (!showTabs) return
    const current = searchParams.get('role')
    if (current !== role) {
      const next = new URLSearchParams(searchParams)
      next.set('role', role)
      setSearchParams(next, { replace: true })
    }
  }, [role, showTabs, searchParams, setSearchParams])

  const headerSubtitle = useMemo(() => {
    if (role === 'advertiser') {
      return 'Инсайты по вашим рекламным кампаниям — что работает, что стоит изменить.'
    }
    return 'Инсайты по вашим каналам — динамика, аномалии, рекомендации по каждому.'
  }, [role])

  if (userLoading) {
    return (
      <div className="max-w-[1280px] mx-auto space-y-4">
        <Skeleton className="h-16" />
        <Skeleton className="h-56" />
        <Skeleton className="h-64" />
      </div>
    )
  }

  if (userError || !user) {
    return (
      <div className="max-w-[1280px] mx-auto">
        <Notification type="danger">Не удалось загрузить данные пользователя.</Notification>
      </div>
    )
  }

  return (
    <div className="max-w-[1280px] mx-auto space-y-5">
      <ScreenHeader
        title="Аналитика"
        subtitle={headerSubtitle}
        action={showTabs ? <RoleTabs role={role} onChange={setRole} /> : undefined}
      />

      <AIInsightCard role={role} />

      <TrendComparison role={role} />

      <ChannelDeepDive role={role} />
    </div>
  )
}
