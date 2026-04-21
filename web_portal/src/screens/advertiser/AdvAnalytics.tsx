import {
  Notification,
  Skeleton,
  Button,
  Icon,
  ScreenHeader,
} from '@shared/ui'
import type { IconName } from '@shared/ui'
import { formatCurrency, formatCompact } from '@/lib/constants'
import { useAdvertiserAnalytics } from '@/hooks/useAnalyticsQueries'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

function getCtrTone(ctr: number): 'success' | 'warning' | 'danger' {
  if (ctr > 0.02) return 'success'
  if (ctr > 0.01) return 'warning'
  return 'danger'
}

const toneClass: Record<'success' | 'warning' | 'danger', string> = {
  success: 'text-success',
  warning: 'text-warning',
  danger: 'text-danger',
}

export default function AdvAnalytics() {
  const { data: analytics, isLoading, isError, refetch } = useAdvertiserAnalytics()
  const topChannel = analytics?.top_channels[0]

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
        <Skeleton className="h-48" />
      </div>
    )
  }

  if (isError) {
    return (
      <div className="max-w-[1280px] mx-auto">
        <Notification type="danger">
          Не удалось загрузить аналитику.{' '}
          <Button variant="secondary" size="sm" iconLeft="refresh" onClick={() => refetch()}>
            Повторить
          </Button>
        </Notification>
      </div>
    )
  }

  if (!analytics) return null

  const chartData = analytics.top_channels.map((ch) => ({
    name: `@${ch.channel.username}`,
    spent: ch.spent,
    reach: ch.reach,
  }))

  return (
    <div className="max-w-[1280px] mx-auto">
      <ScreenHeader
        title="Аналитика рекламодателя"
        subtitle="Сводка по активным и завершённым кампаниям"
        action={
          <Button
            variant="ghost"
            size="sm"
            icon
            onClick={() => refetch()}
            title="Обновить"
            aria-label="Обновить"
          >
            <Icon name="refresh" size={14} />
          </Button>
        }
      />

      <div
        className="grid gap-3.5 mb-5"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}
      >
        <SummaryTile
          icon="campaign"
          tone="accent"
          label="Кампаний"
          value={String(analytics.total_campaigns)}
          delta="Всего за период"
        />
        <SummaryTile
          icon="reach"
          tone="accent2"
          label="Охват"
          value={formatCompact(analytics.total_reach)}
          delta="Совокупно по каналам"
        />
        <SummaryTile
          icon="ctr"
          tone="success"
          label="CTR"
          value={`${(analytics.avg_ctr * 100).toFixed(2)}%`}
          delta="Средний по кампаниям"
        />
        <SummaryTile
          icon="ruble"
          tone="warning"
          label="Потрачено"
          value={formatCurrency(analytics.total_spent)}
          delta="Сумма эскроу-расходов"
        />
      </div>

      {chartData.length > 0 && (
        <div className="bg-harbor-card border border-border rounded-xl overflow-hidden mb-5">
          <div className="px-5 py-3 border-b border-border flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Icon name="analytics" size={14} className="text-text-tertiary" />
              <span className="font-display text-[14px] font-semibold text-text-primary">
                Расходы по каналам
              </span>
            </div>
            <span className="text-[11px] text-text-tertiary">Топ {chartData.length}</span>
          </div>
          <div className="p-4">
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
          </div>
        </div>
      )}

      {analytics.top_channels.length > 0 && (
        <div className="bg-harbor-card border border-border rounded-xl overflow-hidden mb-5">
          <div className="px-5 py-3 border-b border-border flex items-center gap-2">
            <Icon name="channels" size={14} className="text-text-tertiary" />
            <span className="font-display text-[14px] font-semibold text-text-primary">
              Топ каналов по охвату
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-harbor-secondary">
                <tr className="text-[11px] uppercase tracking-[0.08em] text-text-tertiary font-semibold">
                  <th className="text-left px-4 py-2.5">Канал</th>
                  <th className="text-right px-4 py-2.5 hidden md:table-cell">Подписчики</th>
                  <th className="text-right px-4 py-2.5">Охват</th>
                  <th className="text-right px-4 py-2.5">CTR</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {analytics.top_channels.map((ch) => {
                  const tone = getCtrTone(ch.ctr)
                  return (
                    <tr
                      key={ch.channel.id}
                      className="hover:bg-harbor-elevated/40 transition-colors"
                    >
                      <td className="px-4 py-3">
                        <p className="font-medium text-text-primary">@{ch.channel.username}</p>
                        <p className="text-xs text-text-tertiary truncate">{ch.channel.title}</p>
                      </td>
                      <td className="px-4 py-3 text-right text-text-secondary font-mono tabular-nums hidden md:table-cell">
                        {formatCompact(ch.channel.member_count)}
                      </td>
                      <td className="px-4 py-3 text-right text-text-primary font-mono font-medium tabular-nums">
                        {formatCompact(ch.reach)}
                      </td>
                      <td className={`px-4 py-3 text-right font-mono font-semibold tabular-nums ${toneClass[tone]}`}>
                        {(ch.ctr * 100).toFixed(1)}%
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {topChannel && (
        <Notification type="success">
          AI-рекомендация: увеличьте бюджет на канал @{topChannel.channel.username} — высокий CTR {(topChannel.ctr * 100).toFixed(1)}%.
        </Notification>
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
