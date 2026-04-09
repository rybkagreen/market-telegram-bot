import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, StatusPill, Notification, Skeleton } from '@shared/ui'
import { useMyDisputes } from '@/hooks/useDisputeQueries'

const DISPUTE_REASON_LABELS: Record<string, string> = {
  not_published: 'Не опубликовано',
  wrong_time: 'Нарушение времени',
  wrong_text: 'Изменён текст',
  early_deletion: 'Досрочное удаление',
  other: 'Другое',
}

const STATUS_FILTERS = [
  { key: 'all', label: 'Все' },
  { key: 'open', label: 'Открытые' },
  { key: 'owner_explained', label: 'Ожидание' },
  { key: 'resolved', label: 'Решённые' },
  { key: 'closed', label: 'Закрытые' },
] as const

const STATUS_CONFIG: Record<string, { color: string; label: string }> = {
  open: { color: 'danger', label: 'Открыт' },
  owner_explained: { color: 'info', label: 'Владелец ответил' },
  resolved: { color: 'success', label: 'Решён' },
  closed: { color: 'neutral', label: 'Закрыт' },
}

function formatDate(dt: string): string {
  return new Date(dt).toLocaleDateString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

export default function MyDisputes() {
  const navigate = useNavigate()
  const [statusFilter, setStatusFilter] = useState('all')

  const { data, isLoading } = useMyDisputes(statusFilter, 50, 0)
  const disputes = data?.items ?? []

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-12" />
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
      </div>
    )
  }

  if (disputes.length === 0) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-display font-bold text-text-primary">Мои споры</h1>
        <Notification type="info">
          <span className="text-sm">
            {statusFilter === 'all'
              ? 'У вас пока нет споров'
              : `Нет споров со статусом «${STATUS_FILTERS.find((f) => f.key === statusFilter)?.label}»`}
          </span>
        </Notification>
        <button
          className="text-sm text-text-secondary hover:text-text-primary transition-colors"
          onClick={() => navigate(-1)}
        >
          ← Назад
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-display font-bold text-text-primary">Мои споры</h1>

      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.key}
            className={`px-3 py-1.5 rounded-full text-sm border transition-all ${
              statusFilter === f.key
                ? 'bg-accent text-white border-accent'
                : 'border-border text-text-secondary hover:border-accent/50'
            }`}
            onClick={() => setStatusFilter(f.key)}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Dispute cards */}
      <div className="space-y-3">
        {disputes.map((d) => {
          const cfg = STATUS_CONFIG[d.status]
          const reasonLabel = DISPUTE_REASON_LABELS[d.reason as string] ?? d.reason

          return (
            <Card
              key={d.id}
              onClick={() => navigate(`/disputes/${d.id}`)}
              className="cursor-pointer hover:border-accent/50 transition-all"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-mono text-sm font-semibold text-text-primary">
                      #{d.id}
                    </span>
                    <StatusPill status={cfg.color as any}>{cfg.label}</StatusPill>
                  </div>
                  <p className="text-sm text-text-primary">{reasonLabel}</p>
                  <div className="flex items-center gap-4 mt-2 text-xs text-text-secondary">
                    <span>Дата: {formatDate(d.created_at)}</span>
                    {d.owner_comment && <span>· Ответ: ✅</span>}
                    {d.resolution && <span>· Решение: {d.resolution}</span>}
                  </div>
                </div>
              </div>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
