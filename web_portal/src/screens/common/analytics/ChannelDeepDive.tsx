import { useMemo } from 'react'
import { Icon, Notification, Skeleton } from '@shared/ui'
import {
  useAdvertiserAnalytics,
  useOwnerAnalytics,
  useAIInsights,
} from '@/hooks/useAnalyticsQueries'
import { formatCompact, formatCurrency } from '@/lib/constants'
import type { InsightsRole, InsightsChannelFlag } from '@/api/analytics'

interface ChannelDeepDiveProps {
  role: InsightsRole
}

export function ChannelDeepDive({ role }: ChannelDeepDiveProps) {
  return role === 'advertiser' ? <AdvertiserTable /> : <OwnerTable />
}

function flagBadge(flag?: InsightsChannelFlag) {
  if (!flag) return null
  const styles: Record<InsightsChannelFlag['flag'], string> = {
    hot: 'bg-success-muted text-success',
    warn: 'bg-warning-muted text-warning',
    idle: 'bg-harbor-elevated text-text-tertiary',
    neutral: 'bg-harbor-elevated text-text-secondary',
  }
  const labels: Record<InsightsChannelFlag['flag'], string> = {
    hot: '🔥 В топе',
    warn: '⚠️ Внимание',
    idle: '💤 Тишина',
    neutral: 'В норме',
  }
  return (
    <span
      className={[
        'px-2 py-0.5 rounded-full text-[11px] font-semibold',
        styles[flag.flag],
      ].join(' ')}
      title={flag.reason}
    >
      {labels[flag.flag]}
    </span>
  )
}

function AdvertiserTable() {
  const { data, isLoading, isError } = useAdvertiserAnalytics()
  const { data: insights } = useAIInsights('advertiser')
  const flagMap = useMemo(() => {
    const map = new Map<number, InsightsChannelFlag>()
    for (const f of insights?.channel_flags ?? []) map.set(f.channel_id, f)
    return map
  }, [insights])

  if (isLoading) return <Skeleton className="h-56 rounded-xl" />
  if (isError || !data) {
    return <Notification type="warning">Нет данных по каналам.</Notification>
  }
  if (!data.top_channels.length) {
    return (
      <div className="rounded-xl border border-dashed border-border/70 p-6 text-center text-text-tertiary text-sm">
        Здесь появится подробная статистика по каждому каналу, когда завершится первая кампания.
      </div>
    )
  }

  return (
    <section className="bg-harbor-card border border-border rounded-xl overflow-hidden">
      <header className="px-5 py-3 border-b border-border flex items-center gap-2">
        <Icon name="channels" size={14} className="text-text-tertiary" />
        <span className="font-display text-[14px] font-semibold text-text-primary">
          Каналы — где вы размещались
        </span>
      </header>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-harbor-secondary">
            <tr className="text-[11px] uppercase tracking-[0.08em] text-text-tertiary font-semibold">
              <th className="text-left px-4 py-2.5 sticky left-0 bg-harbor-secondary z-10">Канал</th>
              <th className="text-right px-4 py-2.5 hidden md:table-cell">Подписчики</th>
              <th className="text-right px-4 py-2.5">Охват</th>
              <th className="text-right px-4 py-2.5">CTR</th>
              <th className="text-right px-4 py-2.5">Флаг</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {data.top_channels.map((ch) => {
              const flag = flagMap.get(ch.channel.id)
              return (
                <tr
                  key={ch.channel.id}
                  className="hover:bg-harbor-elevated/40 transition-colors"
                >
                  <td className="px-4 py-3 sticky left-0 bg-harbor-card z-10">
                    <p className="font-medium text-text-primary">@{ch.channel.username}</p>
                    <p className="text-xs text-text-tertiary truncate">{ch.channel.title}</p>
                  </td>
                  <td className="px-4 py-3 text-right text-text-secondary font-mono tabular-nums hidden md:table-cell">
                    {formatCompact(ch.channel.member_count)}
                  </td>
                  <td className="px-4 py-3 text-right text-text-primary font-mono font-medium tabular-nums">
                    {formatCompact(ch.reach)}
                  </td>
                  <td className="px-4 py-3 text-right font-mono font-semibold tabular-nums text-text-primary">
                    {(ch.ctr * 100).toFixed(1)}%
                  </td>
                  <td className="px-4 py-3 text-right">{flagBadge(flag)}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function OwnerTable() {
  const { data, isLoading, isError } = useOwnerAnalytics()
  const { data: insights } = useAIInsights('owner')
  const flagMap = useMemo(() => {
    const map = new Map<number, InsightsChannelFlag>()
    for (const f of insights?.channel_flags ?? []) map.set(f.channel_id, f)
    return map
  }, [insights])

  if (isLoading) return <Skeleton className="h-56 rounded-xl" />
  if (isError || !data) {
    return <Notification type="warning">Нет данных по каналам.</Notification>
  }
  if (!data.by_channel.length) {
    return (
      <div className="rounded-xl border border-dashed border-border/70 p-6 text-center text-text-tertiary text-sm">
        Подключите первый канал, чтобы увидеть детальную разбивку.
      </div>
    )
  }

  return (
    <section className="bg-harbor-card border border-border rounded-xl overflow-hidden">
      <header className="px-5 py-3 border-b border-border flex items-center gap-2">
        <Icon name="channels" size={14} className="text-text-tertiary" />
        <span className="font-display text-[14px] font-semibold text-text-primary">
          Ваши каналы
        </span>
      </header>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-harbor-secondary">
            <tr className="text-[11px] uppercase tracking-[0.08em] text-text-tertiary font-semibold">
              <th className="text-left px-4 py-2.5 sticky left-0 bg-harbor-secondary z-10">Канал</th>
              <th className="text-right px-4 py-2.5">Публикации</th>
              <th className="text-right px-4 py-2.5">Доход</th>
              <th className="text-right px-4 py-2.5">Флаг</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {data.by_channel.map((row) => {
              const flag = flagMap.get(row.channel.id)
              return (
                <tr
                  key={row.channel.id}
                  className="hover:bg-harbor-elevated/40 transition-colors"
                >
                  <td className="px-4 py-3 sticky left-0 bg-harbor-card z-10">
                    <p className="font-medium text-text-primary">
                      @{row.channel.username}
                    </p>
                    <p className="text-xs text-text-tertiary truncate">
                      {row.channel.title}
                    </p>
                  </td>
                  <td className="px-4 py-3 text-right text-text-primary font-mono tabular-nums">
                    {row.publications}
                  </td>
                  <td className="px-4 py-3 text-right text-text-primary font-mono font-semibold tabular-nums">
                    {formatCurrency(row.earned)}
                  </td>
                  <td className="px-4 py-3 text-right">{flagBadge(flag)}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </section>
  )
}
