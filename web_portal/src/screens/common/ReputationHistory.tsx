import { Card, Skeleton, Notification, EmptyState } from '@shared/ui'
import { formatDateTimeMSK } from '@/lib/constants'
import { useReputationHistory } from '@/hooks/useReputationQueries'

const ACTION_LABELS: Record<string, string> = {
  placement_completed: 'Размещение завершено',
  placement_cancelled: 'Размещение отменено',
  review_positive: 'Положительный отзыв',
  review_negative: 'Отрицательный отзыв',
  dispute_won: 'Спор выигран',
  dispute_lost: 'Спор проигран',
  dispute_resolved: 'Спор решён',
  violation: 'Нарушение правил',
  timeout: 'Нарушение сроков',
  bonus: 'Бонус',
}

const ROLE_LABELS: Record<string, string> = {
  advertiser: 'Рекламодатель',
  owner: 'Владелец канала',
}

function formatDelta(delta: number): { text: string; color: string } {
  const fixed = delta.toFixed(2)
  if (delta > 0) return { text: `+${fixed}`, color: 'text-success' }
  if (delta < 0) return { text: fixed, color: 'text-danger' }
  return { text: '0.00', color: 'text-text-tertiary' }
}

export default function ReputationHistory() {
  const { data: items, isLoading, isError } = useReputationHistory(50, 0)

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10" />
        <Skeleton className="h-24" />
        <Skeleton className="h-24" />
      </div>
    )
  }

  if (isError) {
    return <Notification type="danger">Не удалось загрузить историю репутации</Notification>
  }

  const list = items ?? []

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-display font-bold text-text-primary">История репутации</h1>
        <p className="text-sm text-text-secondary mt-1">
          Последние события, повлиявшие на рейтинг рекламодателя или владельца канала
        </p>
      </div>

      {list.length === 0 ? (
        <EmptyState
          icon="⭐"
          title="История пуста"
          description="Пока нет событий, повлиявших на репутацию"
        />
      ) : (
        <div className="space-y-3">
          {list.map((item) => {
            const delta = formatDelta(item.delta)
            const actionLabel = ACTION_LABELS[item.action] ?? item.action
            const roleLabel = ROLE_LABELS[item.role] ?? item.role
            return (
              <Card key={item.id} className="p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-text-primary">{actionLabel}</p>
                    <p className="text-xs text-text-tertiary mt-0.5">
                      {roleLabel} · {formatDateTimeMSK(item.created_at)}
                    </p>
                    {item.comment && (
                      <p className="text-xs text-text-secondary mt-2">{item.comment}</p>
                    )}
                  </div>
                  <div className="text-right shrink-0">
                    <p className={`text-base font-mono font-semibold ${delta.color}`}>{delta.text}</p>
                    <p className="text-xs text-text-tertiary mt-0.5">
                      {item.score_before.toFixed(1)} → {item.score_after.toFixed(1)}
                    </p>
                  </div>
                </div>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
