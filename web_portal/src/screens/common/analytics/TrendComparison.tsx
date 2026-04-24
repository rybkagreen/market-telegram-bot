import { useMemo } from 'react'
import {
  BarChart,
  Bar,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { Icon, Notification, Skeleton } from '@shared/ui'
import {
  useAdvertiserAnalytics,
  useOwnerAnalytics,
} from '@/hooks/useAnalyticsQueries'
import { formatCompact, formatCurrency } from '@/lib/constants'
import type { InsightsRole } from '@/api/analytics'

interface TrendComparisonProps {
  role: InsightsRole
}

export function TrendComparison({ role }: TrendComparisonProps) {
  return role === 'advertiser' ? <AdvertiserTrend /> : <OwnerTrend />
}

function AdvertiserTrend() {
  const { data, isLoading, isError } = useAdvertiserAnalytics()
  const bars = useMemo(() => {
    if (!data) return []
    return data.top_channels.slice(0, 5).map((ch) => ({
      name: `@${ch.channel.username}`,
      reach: ch.reach,
      ctr: +(ch.ctr * 100).toFixed(2),
    }))
  }, [data])

  if (isLoading) return <Skeleton className="h-64 rounded-xl" />
  if (isError || !data) {
    return <Notification type="warning">Нет данных для графика.</Notification>
  }
  if (!bars.length) {
    return null
  }

  return (
    <section className="bg-harbor-card border border-border rounded-xl overflow-hidden">
      <header className="px-5 py-3 border-b border-border flex items-center gap-2">
        <Icon name="analytics" size={14} className="text-text-tertiary" />
        <span className="font-display text-[14px] font-semibold text-text-primary">
          Охват по топ-каналам
        </span>
      </header>
      <div className="p-4">
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={bars} margin={{ top: 4, right: 16, left: 0, bottom: 40 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 11, fill: 'var(--color-text-secondary, #94a3b8)' }}
              angle={-30}
              textAnchor="end"
              interval={0}
            />
            <YAxis
              tickFormatter={(v: number) => formatCompact(v)}
              tick={{ fontSize: 11, fill: 'var(--color-text-secondary, #94a3b8)' }}
              width={60}
            />
            <Tooltip
              formatter={(value: unknown) => [formatCompact(Number(value)), 'Охват']}
              contentStyle={{
                background: 'var(--color-harbor-card, #1e293b)',
                border: '1px solid var(--color-border, #334155)',
                borderRadius: 8,
                color: 'var(--color-text-primary, #f1f5f9)',
              }}
            />
            <Bar dataKey="reach" fill="var(--color-accent, #6366f1)" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}

function OwnerTrend() {
  const { data, isLoading, isError } = useOwnerAnalytics()
  const bars = useMemo(() => {
    if (!data) return []
    return data.by_channel
      .map((row) => ({
        name: `@${row.channel.username}`,
        earned: Number(row.earned),
        publications: row.publications,
      }))
      .sort((a, b) => b.earned - a.earned)
      .slice(0, 5)
  }, [data])

  if (isLoading) return <Skeleton className="h-64 rounded-xl" />
  if (isError || !data) {
    return <Notification type="warning">Нет данных для графика.</Notification>
  }
  if (!bars.length) return null

  return (
    <section className="bg-harbor-card border border-border rounded-xl overflow-hidden">
      <header className="px-5 py-3 border-b border-border flex items-center gap-2">
        <Icon name="analytics" size={14} className="text-text-tertiary" />
        <span className="font-display text-[14px] font-semibold text-text-primary">
          Доход по топ-каналам
        </span>
      </header>
      <div className="p-4">
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={bars} margin={{ top: 4, right: 16, left: 0, bottom: 40 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 11, fill: 'var(--color-text-secondary, #94a3b8)' }}
              angle={-30}
              textAnchor="end"
              interval={0}
            />
            <YAxis
              tickFormatter={(v: number) => formatCurrency(v)}
              tick={{ fontSize: 11, fill: 'var(--color-text-secondary, #94a3b8)' }}
              width={80}
            />
            <Tooltip
              formatter={(value: unknown) => [formatCurrency(Number(value)), 'Доход']}
              contentStyle={{
                background: 'var(--color-harbor-card, #1e293b)',
                border: '1px solid var(--color-border, #334155)',
                borderRadius: 8,
                color: 'var(--color-text-primary, #f1f5f9)',
              }}
            />
            <Bar dataKey="earned" fill="var(--color-accent-2, #10b981)" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}
