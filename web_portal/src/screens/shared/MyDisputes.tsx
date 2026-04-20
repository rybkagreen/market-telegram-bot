import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Notification,
  Skeleton,
  Icon,
  ScreenHeader,
  EmptyState,
} from '@shared/ui'
import type { IconName } from '@shared/ui'
import { formatDateTimeMSK } from '@/lib/constants'
import { useMyDisputes } from '@/hooks/useDisputeQueries'

const DISPUTE_REASON_LABELS: Record<string, string> = {
  not_published: 'Не опубликовано',
  wrong_time: 'Нарушение времени',
  wrong_text: 'Изменён текст',
  early_deletion: 'Досрочное удаление',
  post_removed_early: 'Пост удалён досрочно',
  bot_kicked: 'Бот удалён из канала',
  advertiser_complaint: 'Жалоба рекламодателя',
  other: 'Другое',
}

type Filter = 'all' | 'open' | 'owner_explained' | 'resolved' | 'closed'

const STATUS_FILTERS: { key: Filter; label: string }[] = [
  { key: 'all', label: 'Все' },
  { key: 'open', label: 'Открытые' },
  { key: 'owner_explained', label: 'Ожидание' },
  { key: 'resolved', label: 'Решённые' },
  { key: 'closed', label: 'Закрытые' },
]

type Tone = 'danger' | 'warning' | 'success' | 'neutral'

const STATUS_CONFIG: Record<string, { tone: Tone; label: string; icon: IconName }> = {
  open: { tone: 'danger', label: 'Открыт', icon: 'warning' },
  owner_explained: { tone: 'warning', label: 'Ответ владельца', icon: 'hourglass' },
  resolved: { tone: 'success', label: 'Решён', icon: 'check' },
  closed: { tone: 'neutral', label: 'Закрыт', icon: 'archive' },
}

const toneClasses: Record<Tone, string> = {
  danger: 'bg-danger-muted text-danger',
  warning: 'bg-warning-muted text-warning',
  success: 'bg-success-muted text-success',
  neutral: 'bg-harbor-elevated text-text-tertiary',
}

export default function MyDisputes() {
  const navigate = useNavigate()
  const [statusFilter, setStatusFilter] = useState<Filter>('all')

  const { data, isLoading } = useMyDisputes(statusFilter, 50, 0)
  const disputes = data?.items ?? []

  const counts = useMemo(() => {
    const all = disputes.length
    const open = disputes.filter((d) => d.status === 'open').length
    const ownerExplained = disputes.filter((d) => d.status === 'owner_explained').length
    const resolved = disputes.filter((d) => d.status === 'resolved').length
    return { all, open, ownerExplained, resolved }
  }, [disputes])

  return (
    <div className="max-w-[1080px] mx-auto">
      <ScreenHeader
        crumbs={['Главная', 'Споры']}
        title="Мои споры"
        subtitle="Оспорьте публикации, на которые у вас есть претензии — ответ владельца и решение администратора"
      />

      <div className="bg-harbor-card border border-border rounded-xl p-3.5 mb-4 flex items-center gap-3 flex-wrap">
        <div className="flex gap-1.5 flex-wrap">
          {STATUS_FILTERS.map((f) => {
            const on = statusFilter === f.key
            return (
              <button
                key={f.key}
                type="button"
                onClick={() => setStatusFilter(f.key)}
                className={`inline-flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded-2xl border transition-all ${
                  on
                    ? 'border-accent bg-accent-muted text-accent'
                    : 'border-border bg-transparent text-text-secondary hover:border-border-active'
                }`}
              >
                {f.label}
                {f.key !== 'all' && f.key === 'open' && (
                  <span className="font-mono tabular-nums text-[11px] opacity-80">{counts.open}</span>
                )}
                {f.key === 'all' && (
                  <span className="font-mono tabular-nums text-[11px] opacity-80">{counts.all}</span>
                )}
              </button>
            )
          })}
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-20" />
          <Skeleton className="h-20" />
        </div>
      ) : disputes.length === 0 ? (
        <EmptyState
          icon="disputes"
          title="Нет споров"
          description={
            statusFilter === 'all'
              ? 'У вас пока нет споров. Открыть спор можно в течение 48 часов после публикации.'
              : `Нет споров со статусом «${STATUS_FILTERS.find((f) => f.key === statusFilter)?.label}».`
          }
        />
      ) : (
        <div className="bg-harbor-card border border-border rounded-xl overflow-hidden">
          {disputes.map((d, i) => {
            const cfg = STATUS_CONFIG[d.status] ?? {
              tone: 'neutral' as Tone,
              label: d.status,
              icon: 'info' as IconName,
            }
            const reasonLabel = DISPUTE_REASON_LABELS[d.reason as string] ?? d.reason
            return (
              <button
                key={d.id}
                type="button"
                onClick={() => navigate(`/disputes/${d.id}`)}
                className={`w-full text-left flex items-center gap-4 px-[18px] py-3.5 hover:bg-harbor-elevated/40 transition-colors ${i === disputes.length - 1 ? '' : 'border-b border-border'}`}
              >
                <span
                  className={`grid place-items-center w-10 h-10 rounded-[10px] flex-shrink-0 ${toneClasses[cfg.tone]}`}
                >
                  <Icon name={cfg.icon} size={16} />
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-baseline gap-2.5 flex-wrap">
                    <span className="text-[13.5px] font-semibold text-text-primary">
                      {reasonLabel}
                    </span>
                    <span className="font-mono text-[11px] text-text-tertiary py-px px-1.5 rounded bg-harbor-elevated">
                      #{d.id}
                    </span>
                  </div>
                  <div className="text-[11.5px] text-text-tertiary mt-0.5 flex items-center gap-3 flex-wrap">
                    <span>{formatDateTimeMSK(d.created_at)} МСК</span>
                    {d.owner_explanation && (
                      <span className="flex items-center gap-1 text-success">
                        <Icon name="check" size={11} /> Ответ владельца
                      </span>
                    )}
                    {d.resolution && (
                      <span className="flex items-center gap-1 text-accent">
                        <Icon name="verified" size={11} /> Решено
                      </span>
                    )}
                  </div>
                </div>
                <span
                  className={`text-[10.5px] font-bold tracking-[0.08em] uppercase py-1 px-2 rounded whitespace-nowrap ${toneClasses[cfg.tone]}`}
                >
                  {cfg.label}
                </span>
                <Icon name="chevron-right" size={14} className="text-text-tertiary flex-shrink-0" />
              </button>
            )
          })}
        </div>
      )}

      {disputes.length > 0 && statusFilter === 'open' && (
        <div className="mt-4">
          <Notification type="info">
            Администратор рассмотрит спор в течение 48 часов после получения объяснений владельца.
          </Notification>
        </div>
      )}
    </div>
  )
}
