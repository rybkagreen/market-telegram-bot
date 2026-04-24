import { useNavigate } from 'react-router-dom'
import { Button, Icon, Skeleton, Notification } from '@shared/ui'
import type { IconName } from '@shared/ui'
import { useAIInsights } from '@/hooks/useAnalyticsQueries'
import type { InsightsRole, InsightsActionItem } from '@/api/analytics'

interface AIInsightCardProps {
  role: InsightsRole
}

export function AIInsightCard({ role }: AIInsightCardProps) {
  const { data, isLoading, isError, refetch, isFetching } = useAIInsights(role)
  const navigate = useNavigate()

  if (isLoading) {
    return <Skeleton className="h-56 rounded-2xl" />
  }

  if (isError || !data) {
    return (
      <Notification type="danger">
        Не удалось загрузить AI-инсайты.{' '}
        <Button variant="secondary" size="sm" iconLeft="refresh" onClick={() => refetch()}>
          Повторить
        </Button>
      </Notification>
    )
  }

  const generated = new Date(data.generated_at)
  const minutesAgo = Math.max(0, Math.round((Date.now() - generated.getTime()) / 60_000))
  const backendBadge =
    data.ai_backend === 'mistral' ? (
      <span
        className="px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider bg-accent-muted text-accent"
        title="Ответ сгенерирован Mistral AI"
      >
        AI
      </span>
    ) : (
      <span
        className="px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider bg-harbor-elevated text-text-secondary"
        title="Правило-ориентированный fallback (AI недоступен)"
      >
        Rules
      </span>
    )

  const handleCTA = (item: InsightsActionItem) => {
    switch (item.cta_type) {
      case 'create_campaign':
        navigate('/adv/campaigns/new/category')
        break
      case 'open_channel':
        if (item.channel_id) navigate(`/own/channels/${item.channel_id}`)
        else navigate('/own/channels')
        break
      case 'open_placement':
        if (item.channel_id) navigate(`/adv/campaigns/${item.channel_id}`)
        break
      default:
        break
    }
  }

  return (
    <section className="bg-harbor-card border border-border rounded-2xl p-5 space-y-4">
      <header className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <span className="grid place-items-center w-8 h-8 rounded-lg bg-accent-muted text-accent">
            <Icon name="analytics" size={16} />
          </span>
          <h2 className="font-display text-[16px] font-semibold text-text-primary">
            AI-инсайт
          </h2>
          {backendBadge}
        </div>
        <div className="flex items-center gap-3">
          <span className="text-[11px] text-text-tertiary">
            Обновлено {minutesAgo === 0 ? 'только что' : `${minutesAgo} мин. назад`}
          </span>
          <Button
            variant="ghost"
            size="sm"
            iconLeft="refresh"
            onClick={() => refetch()}
            disabled={isFetching}
          >
            Обновить
          </Button>
        </div>
      </header>

      <p className="text-[15px] leading-relaxed text-text-primary">{data.summary}</p>

      {data.action_items.length > 0 && (
        <div className="space-y-2.5">
          {data.action_items.map((item, idx) => (
            <ActionItemRow key={idx} item={item} onCTA={handleCTA} />
          ))}
        </div>
      )}

      {data.forecast && (
        <div className="rounded-xl bg-harbor-elevated/60 border border-border/70 px-4 py-3 flex items-center gap-3">
          <Icon name="growth" size={16} className="text-accent" />
          <div className="flex-1 min-w-0">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-text-tertiary">
              Прогноз на {data.forecast.period_days} дней
            </div>
            <div className="text-[14px] font-semibold text-text-primary tabular-nums">
              {formatForecast(data.forecast.metric, data.forecast.expected_value)}
              <span className="text-text-tertiary font-normal ml-2">
                · уверенность {data.forecast.confidence_pct}%
              </span>
            </div>
          </div>
        </div>
      )}

      {data.anomalies.length > 0 && (
        <div className="space-y-1.5">
          {data.anomalies.map((a, idx) => (
            <div
              key={idx}
              className="flex items-start gap-2 text-[13px]"
            >
              <span
                className={[
                  'inline-block w-2 h-2 rounded-full mt-1.5 flex-shrink-0',
                  a.severity === 'high'
                    ? 'bg-danger'
                    : a.severity === 'medium'
                      ? 'bg-warning'
                      : 'bg-text-tertiary',
                ].join(' ')}
              />
              <span className="text-text-secondary">{a.description}</span>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

function ActionItemRow({
  item,
  onCTA,
}: {
  item: InsightsActionItem
  onCTA: (item: InsightsActionItem) => void
}) {
  return (
    <div className="rounded-xl border border-border/70 px-4 py-3 flex items-start gap-3 hover:bg-harbor-elevated/40 transition-colors">
      <span className="grid place-items-center w-7 h-7 rounded-md bg-harbor-elevated text-text-secondary mt-0.5 flex-shrink-0">
        <Icon name={iconForKind(item.kind)} size={14} />
      </span>
      <div className="flex-1 min-w-0 space-y-0.5">
        <div className="text-[14px] font-semibold text-text-primary">{item.title}</div>
        <div className="text-[12.5px] text-text-secondary">{item.description}</div>
        {item.impact_estimate && (
          <div className="text-[11.5px] font-semibold text-success">{item.impact_estimate}</div>
        )}
      </div>
      {item.cta_type !== 'none' && (
        <Button variant="secondary" size="sm" onClick={() => onCTA(item)}>
          {ctaLabel(item.cta_type)}
        </Button>
      )}
    </div>
  )
}

function iconForKind(kind: InsightsActionItem['kind']): IconName {
  switch (kind) {
    case 'scale':
      return 'growth'
    case 'reallocate':
      return 'share'
    case 'pause':
      return 'pause'
    case 'experiment':
      return 'zap'
    case 'optimize':
      return 'settings'
    default:
      return 'info'
  }
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
      return `${new Intl.NumberFormat('ru-RU').format(Math.round(num))} ₽`
    case 'reach':
      return `${new Intl.NumberFormat('ru-RU').format(Math.round(num))} просмотров`
    case 'ctr':
      return `CTR ${num.toFixed(2)}%`
    default:
      return String(num)
  }
}
