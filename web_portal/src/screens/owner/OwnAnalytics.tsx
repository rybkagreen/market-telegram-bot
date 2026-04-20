import { Notification, Skeleton, Icon, ScreenHeader, Button } from '@shared/ui'
import type { IconName } from '@shared/ui'
import { formatCurrency } from '@/lib/constants'
import { useOwnerAnalytics } from '@/hooks/useAnalyticsQueries'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

export default function OwnAnalytics() {
  const { data: analytics, isLoading, isError, refetch } = useOwnerAnalytics()

  if (isLoading) {
    return (
      <div className="max-w-[1280px] mx-auto space-y-4">
        <Skeleton className="h-16" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
        <Skeleton className="h-64" />
      </div>
    )
  }

  if (isError) {
    return (
      <div className="max-w-[1280px] mx-auto">
        <Notification type="danger">Не удалось загрузить аналитику.</Notification>
      </div>
    )
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
    <div className="max-w-[1280px] mx-auto">
      <ScreenHeader
        title="Аналитика владельца"
        subtitle="Доход по каналам и периодам · комиссия платформы 15% уже учтена"
        action={
          <Button variant="secondary" iconLeft="refresh" onClick={() => refetch()}>
            Обновить
          </Button>
        }
      />

      <div
        className="grid gap-3.5 mb-5"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}
      >
        <SummaryTile
          icon="ruble"
          tone="success"
          label="Заработано"
          value={formatCurrency(analytics.total_earned)}
          delta="Итого за период"
        />
        <SummaryTile
          icon="placement"
          tone="accent"
          label="Публикаций"
          value={String(analytics.total_publications)}
          delta="Успешно доставлено"
        />
        <SummaryTile
          icon="star"
          tone="warning"
          label="Рейтинг"
          value={analytics.avg_rating.toFixed(1)}
          delta="Средняя оценка"
        />
        <SummaryTile
          icon="channels"
          tone="accent2"
          label="Каналов"
          value={String(analytics.channel_count)}
          delta="Под управлением"
        />
      </div>

      <div className="bg-harbor-card border border-border rounded-xl overflow-hidden mb-5">
        <div className="px-5 py-3 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Icon name="analytics" size={14} className="text-text-tertiary" />
            <span className="font-display text-[14px] font-semibold text-text-primary">
              Заработок за период
            </span>
          </div>
        </div>
        <div className="p-4">
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
        </div>
      </div>

      {analytics.by_channel.length > 0 && (
        <>
          {channelChartData.length > 1 && (
            <div className="bg-harbor-card border border-border rounded-xl overflow-hidden mb-5">
              <div className="px-5 py-3 border-b border-border flex items-center gap-2">
                <Icon name="channels" size={14} className="text-text-tertiary" />
                <span className="font-display text-[14px] font-semibold text-text-primary">
                  Доход по каналам
                </span>
              </div>
              <div className="p-4">
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart
                    data={channelChartData}
                    margin={{ top: 4, right: 16, left: 0, bottom: 40 }}
                  >
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
              </div>
            </div>
          )}

          <div className="bg-harbor-card border border-border rounded-xl overflow-hidden">
            <div className="px-5 py-3 border-b border-border flex items-center gap-2">
              <Icon name="channels" size={14} className="text-text-tertiary" />
              <span className="font-display text-[14px] font-semibold text-text-primary">
                По каналам
              </span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-harbor-secondary">
                  <tr className="text-[11px] uppercase tracking-[0.08em] text-text-tertiary font-semibold">
                    <th className="text-left px-4 py-2.5">Канал</th>
                    <th className="text-right px-4 py-2.5">Публикаций</th>
                    <th className="text-right px-4 py-2.5">Доход</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {analytics.by_channel.map((ch) => (
                    <tr
                      key={ch.channel.id}
                      className="hover:bg-harbor-elevated/40 transition-colors"
                    >
                      <td className="px-4 py-3">
                        <p className="font-medium text-text-primary">@{ch.channel.username}</p>
                        <p className="text-xs text-text-tertiary truncate">{ch.channel.title}</p>
                      </td>
                      <td className="px-4 py-3 text-right text-text-secondary font-mono tabular-nums">
                        {ch.publications}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-success font-semibold tabular-nums">
                        {formatCurrency(ch.earned)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

const toneIconBg: Record<'success' | 'warning' | 'accent' | 'accent2', string> = {
  success: 'bg-success-muted text-success',
  warning: 'bg-warning-muted text-warning',
  accent: 'bg-accent-muted text-accent',
  accent2: 'bg-accent-2-muted text-accent-2',
}

function SummaryTile({
  icon,
  tone,
  label,
  value,
  delta,
}: {
  icon: IconName
  tone: 'success' | 'warning' | 'accent' | 'accent2'
  label: string
  value: string
  delta: string
}) {
  return (
    <div className="bg-harbor-card border border-border rounded-xl p-[18px] flex gap-3.5 items-start">
      <span
        className={`grid place-items-center w-[42px] h-[42px] rounded-[10px] flex-shrink-0 ${toneIconBg[tone]}`}
      >
        <Icon name={icon} size={18} />
      </span>
      <div className="flex-1 min-w-0">
        <div className="text-[11px] font-semibold uppercase tracking-wider text-text-tertiary mb-1">
          {label}
        </div>
        <div className="font-display text-xl font-bold text-text-primary tracking-[-0.02em] tabular-nums truncate">
          {value}
        </div>
        <div className="text-[11.5px] text-text-tertiary mt-0.5 truncate">{delta}</div>
      </div>
    </div>
  )
}
