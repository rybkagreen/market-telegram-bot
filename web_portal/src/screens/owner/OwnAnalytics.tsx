import { Card, Notification, Skeleton } from '@shared/ui'
import { formatCurrency } from '@/lib/constants'
import { useOwnerAnalytics } from '@/hooks/useAnalyticsQueries'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'

export default function OwnAnalytics() {
  const { data: analytics, isLoading, isError } = useOwnerAnalytics()

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-24" />)}
        </div>
        <Skeleton className="h-48" />
        <Skeleton className="h-40" />
      </div>
    )
  }

  if (isError) {
    return <Notification type="danger">❌ Не удалось загрузить аналитику</Notification>
  }

  if (!analytics) return null

  const channelChartData = analytics.by_channel.map((ch) => ({
    name: `@${ch.channel.username}`,
    earned: ch.earned,
    publications: ch.publications,
  }))

  const periodChartData = [
    { label: 'Сегодня', value: analytics.earnings_period.today },
    { label: 'Неделя', value: analytics.earnings_period.week },
    { label: 'Месяц', value: analytics.earnings_period.month },
    { label: 'Итого', value: analytics.earnings_period.total },
  ]

  return (
    <div className="space-y-6">
      {/* Page title */}
      <div>
        <h1 className="text-2xl font-display font-bold text-text-primary">Аналитика владельца</h1>
        <p className="text-text-secondary mt-1">Доход и статистика по каналам</p>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-4">
          <p className="text-sm text-text-secondary">Заработано</p>
          <p className="text-2xl font-bold text-success mt-1">{formatCurrency(analytics.total_earned)}</p>
        </Card>
        <Card className="p-4">
          <p className="text-sm text-text-secondary">Публикаций</p>
          <p className="text-2xl font-bold text-text-primary mt-1">{analytics.total_publications}</p>
        </Card>
        <Card className="p-4">
          <p className="text-sm text-text-secondary">Рейтинг</p>
          <p className="text-2xl font-bold text-warning mt-1">{analytics.avg_rating.toFixed(1)} ⭐</p>
        </Card>
        <Card className="p-4">
          <p className="text-sm text-text-secondary">Каналов</p>
          <p className="text-2xl font-bold text-text-primary mt-1">{analytics.channel_count}</p>
        </Card>
      </div>

      {/* Commission note */}
      <Notification type="info">
        ℹ️ Комиссия платформы: 15% (включена в сумму выше)
      </Notification>

      {/* Earnings by period — bar chart */}
      <Card title="Заработок за период">
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={periodChartData} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 12, fill: 'var(--color-text-secondary, #94a3b8)' }}
            />
            <YAxis
              tickFormatter={(v: number) => formatCurrency(v)}
              tick={{ fontSize: 11, fill: 'var(--color-text-secondary, #94a3b8)' }}
              width={70}
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
            <Bar dataKey="value" fill="var(--color-success, #22c55e)" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </Card>

      {/* By channel chart + table */}
      {analytics.by_channel.length > 0 && (
        <>
          {channelChartData.length > 1 && (
            <Card title="Доход по каналам">
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={channelChartData} margin={{ top: 4, right: 16, left: 0, bottom: 40 }}>
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
                    width={70}
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
                  <Bar dataKey="earned" fill="var(--color-accent, #6366f1)" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </Card>
          )}

          <Card title="По каналам" className="p-0 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-harbor-elevated">
                  <tr>
                    <th className="text-left px-4 py-3 text-text-secondary font-medium">Канал</th>
                    <th className="text-right px-4 py-3 text-text-secondary font-medium">Публикаций</th>
                    <th className="text-right px-4 py-3 text-text-secondary font-medium">Доход</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {analytics.by_channel.map((ch) => (
                    <tr key={ch.channel.id} className="hover:bg-harbor-elevated/50 transition-colors">
                      <td className="px-4 py-3">
                        <p className="font-medium text-text-primary">@{ch.channel.username}</p>
                        <p className="text-xs text-text-tertiary">{ch.channel.title}</p>
                      </td>
                      <td className="px-4 py-3 text-right text-text-secondary">{ch.publications}</td>
                      <td className="px-4 py-3 text-right font-mono text-success font-medium">{formatCurrency(ch.earned)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </div>
  )
}
