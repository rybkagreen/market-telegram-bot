import { Card, Notification, Skeleton, Button } from '@shared/ui'
import { formatCurrency, formatCompact, formatPercent } from '@/lib/constants'
import { useAdvertiserAnalytics } from '@/hooks/useAnalyticsQueries'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'

function getCtrColorClass(ctr: number): string {
  if (ctr > 2) return 'text-success'
  if (ctr > 1) return 'text-warning'
  return 'text-danger'
}

export default function AdvAnalytics() {
  const { data: analytics, isLoading, isError, refetch } = useAdvertiserAnalytics()
  const topChannel = analytics?.top_channels[0]

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-24" />)}
        </div>
        <Skeleton className="h-64" />
        <Skeleton className="h-48" />
      </div>
    )
  }

  if (isError) {
    return (
      <Notification type="danger">
        <span>Не удалось загрузить аналитику.</span>{' '}
        <Button variant="secondary" size="sm" onClick={() => refetch()}>Повторить</Button>
      </Notification>
    )
  }

  if (!analytics) return null

  const chartData = analytics.top_channels.map((ch) => ({
    name: `@${ch.channel.username}`,
    spent: ch.spent,
    reach: ch.reach,
  }))

  return (
    <div className="space-y-6">
      {/* Page title */}
      <div>
        <h1 className="text-2xl font-display font-bold text-text-primary">Аналитика рекламодателя</h1>
        <p className="text-text-secondary mt-1">Статистика по кампаниям и размещениям</p>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-4">
          <p className="text-sm text-text-secondary">Кампаний</p>
          <p className="text-2xl font-bold text-text-primary mt-1">{analytics.total_campaigns}</p>
        </Card>
        <Card className="p-4">
          <p className="text-sm text-text-secondary">Охват</p>
          <p className="text-2xl font-bold text-text-primary mt-1">{formatCompact(analytics.total_reach)}</p>
        </Card>
        <Card className="p-4">
          <p className="text-sm text-text-secondary">CTR</p>
          <p className="text-2xl font-bold text-text-primary mt-1">{formatPercent(analytics.avg_ctr)}</p>
        </Card>
        <Card className="p-4">
          <p className="text-sm text-text-secondary">Потрачено</p>
          <p className="text-2xl font-bold text-text-primary mt-1">{formatCurrency(analytics.total_spent)}</p>
        </Card>
      </div>

      {/* Spend by channel — bar chart */}
      {chartData.length > 0 && (
        <Card title="Расходы по каналам">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={chartData} margin={{ top: 4, right: 16, left: 0, bottom: 40 }}>
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
              formatter={(value: unknown) => [formatCurrency(Number(value)), 'Расходы']}
                contentStyle={{
                  background: 'var(--color-harbor-card, #1e293b)',
                  border: '1px solid var(--color-border, #334155)',
                  borderRadius: 8,
                  color: 'var(--color-text-primary, #f1f5f9)',
                }}
              />
              <Bar dataKey="spent" fill="var(--color-accent, #6366f1)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      )}

      {/* Top channels table */}
      {analytics.top_channels.length > 0 && (
        <Card title="Топ каналов по охвату" className="p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-harbor-elevated">
                <tr>
                  <th className="text-left px-4 py-3 text-text-secondary font-medium">Канал</th>
                  <th className="text-left px-4 py-3 text-text-secondary font-medium hidden md:table-cell">Подписчики</th>
                  <th className="text-right px-4 py-3 text-text-secondary font-medium">Охват</th>
                  <th className="text-right px-4 py-3 text-text-secondary font-medium">CTR</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {analytics.top_channels.map((ch) => (
                  <tr key={ch.channel.id} className="hover:bg-harbor-elevated/50 transition-colors">
                    <td className="px-4 py-3">
                      <p className="font-medium text-text-primary">@{ch.channel.username}</p>
                      <p className="text-xs text-text-tertiary">{ch.channel.title}</p>
                    </td>
                    <td className="px-4 py-3 text-text-secondary hidden md:table-cell">
                      {formatCompact(ch.channel.member_count)}
                    </td>
                    <td className="px-4 py-3 text-right text-text-primary font-medium">
                      {formatCompact(ch.reach)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className={getCtrColorClass(ch.ctr)}>
                        {(ch.ctr * 100).toFixed(1)}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* AI recommendation */}
      {topChannel && (
        <Notification type="success">
          ✨ AI-рекомендация: Увеличьте бюджет на IT-каналы (высокий CTR {(topChannel.ctr * 100).toFixed(1)}%)
        </Notification>
      )}
    </div>
  )
}
