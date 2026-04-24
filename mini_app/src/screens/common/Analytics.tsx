import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import {
  Button,
  Card,
  EmptyState,
  Notification,
  Skeleton,
  Text,
} from '@/components/ui'
import {
  useAdvertiserAnalytics,
  useOwnerAnalytics,
  useAIInsights,
} from '@/hooks/queries'
import { formatCurrency, formatCompact, formatPercent } from '@/lib/formatters'
import type {
  InsightsRole,
  InsightsActionItem,
  InsightsChannelFlag,
} from '@/api/analytics'

export default function Analytics() {
  const { data: advData } = useAdvertiserAnalytics()
  const { data: ownerData } = useOwnerAnalytics()

  const hasAdv = (advData?.total_campaigns ?? 0) > 0
  const hasOwner = (ownerData?.channel_count ?? 0) > 0
  const showToggle = hasAdv && hasOwner

  const [searchParams, setSearchParams] = useSearchParams()
  const param = searchParams.get('role')
  const defaultRole: InsightsRole = hasOwner && !hasAdv ? 'owner' : 'advertiser'
  const initial: InsightsRole =
    param === 'owner' || param === 'advertiser' ? (param as InsightsRole) : defaultRole

  const [role, setRole] = useState<InsightsRole>(initial)

  useEffect(() => {
    if (!showToggle) return
    const current = searchParams.get('role')
    if (current !== role) {
      const next = new URLSearchParams(searchParams)
      next.set('role', role)
      setSearchParams(next, { replace: true })
    }
  }, [role, showToggle, searchParams, setSearchParams])

  return (
    <ScreenShell>
      {showToggle && (
        <div className="flex gap-2 mb-3">
          <RoleButton active={role === 'advertiser'} onClick={() => setRole('advertiser')}>
            Реклама
          </RoleButton>
          <RoleButton active={role === 'owner'} onClick={() => setRole('owner')}>
            Каналы
          </RoleButton>
        </div>
      )}

      <AIInsightSection role={role} />

      {role === 'advertiser' ? (
        <AdvertiserChannels />
      ) : (
        <OwnerChannels />
      )}
    </ScreenShell>
  )
}

function RoleButton({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      className={[
        'px-4 py-1.5 rounded-full text-sm font-semibold transition-colors',
        active
          ? 'bg-blue-600 text-white'
          : 'bg-neutral-800 text-neutral-300',
      ].join(' ')}
    >
      {children}
    </button>
  )
}

function AIInsightSection({ role }: { role: InsightsRole }) {
  const { data, isLoading, isError, refetch, isFetching } = useAIInsights(role)
  const navigate = useNavigate()

  if (isLoading) return <Skeleton height={160} radius="lg" />
  if (isError || !data) {
    return (
      <Notification type="danger">
        <Text variant="sm">Не удалось загрузить AI-инсайты.</Text>{' '}
        <Button variant="secondary" size="sm" onClick={() => refetch()}>
          Повторить
        </Button>
      </Notification>
    )
  }

  const generated = new Date(data.generated_at)
  const minutesAgo = Math.max(0, Math.round((Date.now() - generated.getTime()) / 60_000))

  const handleCTA = (item: InsightsActionItem) => {
    switch (item.cta_type) {
      case 'create_campaign':
        navigate('/adv/campaigns/new/category')
        break
      case 'open_channel':
        if (item.channel_id) navigate(`/own/channels/${item.channel_id}`)
        else navigate('/own/channels')
        break
      default:
        break
    }
  }

  return (
    <Card>
      <div className="flex items-center justify-between gap-2 mb-2 flex-wrap">
        <div className="flex items-center gap-2">
          <span className="text-base font-semibold">✨ AI-инсайт</span>
          <span
            className={[
              'px-2 py-0.5 text-[10px] rounded-full font-semibold uppercase',
              data.ai_backend === 'mistral'
                ? 'bg-indigo-500/20 text-indigo-300'
                : 'bg-neutral-700 text-neutral-300',
            ].join(' ')}
          >
            {data.ai_backend === 'mistral' ? 'AI' : 'Rules'}
          </span>
        </div>
        <Button variant="secondary" size="sm" onClick={() => refetch()} disabled={isFetching}>
          Обновить
        </Button>
      </div>

      <Text variant="sm">{data.summary}</Text>

      {data.action_items.length > 0 && (
        <div className="mt-3 space-y-2">
          {data.action_items.map((item, idx) => (
            <div
              key={idx}
              className="p-3 rounded-lg bg-neutral-900/60 border border-neutral-800"
            >
              <div className="font-semibold text-sm">{item.title}</div>
              <Text variant="xs">{item.description}</Text>
              {item.impact_estimate && (
                <div className="text-[11px] font-semibold text-green-400 mt-1">
                  {item.impact_estimate}
                </div>
              )}
              {item.cta_type !== 'none' && (
                <div className="mt-2">
                  <Button size="sm" variant="secondary" onClick={() => handleCTA(item)}>
                    {ctaLabel(item.cta_type)}
                  </Button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {data.forecast && (
        <div className="mt-3 flex items-center justify-between text-sm border-t border-neutral-800 pt-2">
          <span className="text-neutral-400">
            Прогноз на {data.forecast.period_days} дн.
          </span>
          <span className="font-semibold">
            {formatForecast(data.forecast.metric, data.forecast.expected_value)}
            <span className="text-neutral-500 font-normal ml-1">
              · {data.forecast.confidence_pct}%
            </span>
          </span>
        </div>
      )}

      {data.anomalies.length > 0 && (
        <div className="mt-3 space-y-1">
          {data.anomalies.map((a, idx) => (
            <Text key={idx} variant="xs">
              {a.severity === 'high' ? '🔴' : a.severity === 'medium' ? '🟡' : '⚪'}{' '}
              {a.description}
            </Text>
          ))}
        </div>
      )}

      <div className="mt-2 text-[10px] text-neutral-500">
        Обновлено {minutesAgo === 0 ? 'только что' : `${minutesAgo} мин. назад`}
      </div>
    </Card>
  )
}

function AdvertiserChannels() {
  const { data, isLoading, isError } = useAdvertiserAnalytics()
  const { data: insights } = useAIInsights('advertiser')
  const flagMap = useMemo(() => {
    const m = new Map<number, InsightsChannelFlag>()
    for (const f of insights?.channel_flags ?? []) m.set(f.channel_id, f)
    return m
  }, [insights])

  if (isLoading) return <Skeleton height={200} radius="lg" />
  if (isError || !data) {
    return <Notification type="danger"><Text variant="sm">Нет данных по каналам</Text></Notification>
  }
  if (!data.top_channels.length) {
    return (
      <EmptyState
        icon="📊"
        title="Пока нет кампаний"
        description="Запустите первую кампанию, чтобы увидеть аналитику по каналам."
      />
    )
  }

  return (
    <>
      <p className="text-sm font-semibold mt-4 mb-2">Топ каналов</p>
      <Card>
        {data.top_channels.map((ch) => {
          const flag = flagMap.get(ch.channel.id)
          return (
            <div
              key={ch.channel.id}
              className="flex items-center justify-between gap-2 py-2 border-b border-neutral-800 last:border-b-0"
            >
              <div className="min-w-0 flex-1">
                <div className="font-semibold text-sm truncate">@{ch.channel.username}</div>
                <div className="text-[11px] text-neutral-400 truncate">{ch.channel.title}</div>
              </div>
              <div className="text-right shrink-0">
                <div className="text-sm font-semibold">{formatCompact(ch.reach)}</div>
                <div className="text-[11px] text-neutral-400">
                  CTR {formatPercent(ch.ctr)}
                </div>
              </div>
              {flag && <FlagBadge flag={flag} />}
            </div>
          )
        })}
      </Card>
    </>
  )
}

function OwnerChannels() {
  const { data, isLoading, isError } = useOwnerAnalytics()
  const { data: insights } = useAIInsights('owner')
  const flagMap = useMemo(() => {
    const m = new Map<number, InsightsChannelFlag>()
    for (const f of insights?.channel_flags ?? []) m.set(f.channel_id, f)
    return m
  }, [insights])

  if (isLoading) return <Skeleton height={200} radius="lg" />
  if (isError || !data) {
    return <Notification type="danger"><Text variant="sm">Нет данных по каналам</Text></Notification>
  }
  if (!data.by_channel.length) {
    return (
      <EmptyState
        icon="📡"
        title="Ещё нет каналов"
        description="Подключите первый канал, чтобы начать зарабатывать."
      />
    )
  }

  return (
    <>
      <p className="text-sm font-semibold mt-4 mb-2">Ваши каналы</p>
      <Card>
        {data.by_channel.map((ch) => {
          const flag = flagMap.get(ch.channel.id)
          return (
            <div
              key={ch.channel.id}
              className="flex items-center justify-between gap-2 py-2 border-b border-neutral-800 last:border-b-0"
            >
              <div className="min-w-0 flex-1">
                <div className="font-semibold text-sm truncate">@{ch.channel.username}</div>
                <div className="text-[11px] text-neutral-400 truncate">{ch.channel.title}</div>
              </div>
              <div className="text-right shrink-0">
                <div className="text-sm font-semibold">{formatCurrency(ch.earned)}</div>
                <div className="text-[11px] text-neutral-400">
                  {ch.publications} публ.
                </div>
              </div>
              {flag && <FlagBadge flag={flag} />}
            </div>
          )
        })}
      </Card>
    </>
  )
}

function FlagBadge({ flag }: { flag: InsightsChannelFlag }) {
  const styles: Record<InsightsChannelFlag['flag'], string> = {
    hot: 'bg-emerald-500/20 text-emerald-300',
    warn: 'bg-amber-500/20 text-amber-300',
    idle: 'bg-neutral-700 text-neutral-300',
    neutral: 'bg-neutral-800 text-neutral-400',
  }
  const labels: Record<InsightsChannelFlag['flag'], string> = {
    hot: '🔥',
    warn: '⚠️',
    idle: '💤',
    neutral: '—',
  }
  return (
    <span
      className={[
        'inline-flex items-center justify-center w-7 h-7 rounded-full text-xs shrink-0',
        styles[flag.flag],
      ].join(' ')}
      title={flag.reason}
    >
      {labels[flag.flag]}
    </span>
  )
}

function ctaLabel(cta: InsightsActionItem['cta_type']): string {
  switch (cta) {
    case 'create_campaign':
      return 'Создать'
    case 'open_channel':
      return 'К каналу'
    case 'open_placement':
      return 'К кампании'
    default:
      return ''
  }
}

function formatForecast(metric: string, value: string): string {
  const num = Number(value)
  if (Number.isNaN(num)) return value
  switch (metric) {
    case 'earnings':
    case 'spend':
      return formatCurrency(num)
    case 'reach':
      return `${formatCompact(num)} просм.`
    case 'ctr':
      return `CTR ${num.toFixed(2)}%`
    default:
      return String(num)
  }
}
