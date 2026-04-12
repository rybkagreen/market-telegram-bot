import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Button, Skeleton, Notification, StatusBadge } from '@shared/ui'
import { formatDateMSK } from '@/lib/constants'
import { useAdminDisputes } from '@/hooks/useFeedbackQueries'

type StatusFilter = 'all' | 'open' | 'owner_reply' | 'resolved'

export default function AdminDisputesList() {
  const navigate = useNavigate()
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('open')
  const [page, setPage] = useState(0)
  const limit = 20

  const { data, isLoading, error } = useAdminDisputes({
    status: statusFilter === 'all' ? undefined : statusFilter,
    limit,
    offset: page * limit,
  })

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-12" />
        <Skeleton className="h-96" />
      </div>
    )
  }

  if (error || !data) {
    return <Notification type="danger">Не удалось загрузить список споров.</Notification>
  }

  const statusLabels: Record<StatusFilter, string> = {
    all: 'Все',
    open: 'Открытые',
    owner_reply: 'Ответ владельца',
    resolved: 'Решённые',
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-display font-bold text-text-primary">Споры</h1>
        <p className="text-text-secondary mt-1">Всего: {data.total}</p>
      </div>

      {/* Filter buttons */}
      <div className="flex gap-2 flex-wrap">
        {(['all', 'open', 'owner_reply', 'resolved'] as StatusFilter[]).map((status) => (
          <button
            key={status}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              statusFilter === status
                ? 'bg-accent text-accent-text'
                : 'bg-harbor-elevated text-text-secondary hover:text-text-primary'
            }`}
            onClick={() => { setStatusFilter(status); setPage(0) }}
          >
            {statusLabels[status]}
          </button>
        ))}
      </div>

      {/* Disputes list */}
      <Card className="p-0 overflow-hidden">
        {data.items.length === 0 ? (
          <div className="px-5 py-8 text-center text-text-secondary">Споры не найдены</div>
        ) : (
          <div className="divide-y divide-border">
            {data.items.map((dispute) => (
              <div
                key={dispute.id}
                className="px-5 py-4 hover:bg-harbor-elevated/50 transition-colors cursor-pointer"
                onClick={() => navigate(`/disputes/${dispute.id}`)}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') navigate(`/disputes/${dispute.id}`) }}
                tabIndex={0}
                role="button"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-mono text-text-tertiary">#{dispute.id}</span>
                      <StatusBadge status={dispute.status} />
                    </div>
                    <p className="text-sm text-text-primary truncate">{dispute.reason}</p>
                    <div className="flex gap-4 mt-1 text-xs text-text-tertiary">
                      <span>Рекламодатель: #{dispute.advertiser_id}</span>
                      <span>Владелец: #{dispute.owner_id}</span>
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-xs text-text-tertiary">
                      {formatDateMSK(dispute.created_at)}
                    </p>
                    <Button size="sm" variant="secondary" className="mt-2">
                      {dispute.status === 'resolved' ? 'Просмотр' : 'Решить'}
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Pagination */}
      {data.total > limit && (
        <div className="flex items-center justify-between">
          <Button size="sm" variant="secondary" disabled={page === 0} onClick={() => setPage(page - 1)}>
            ← Назад
          </Button>
          <span className="text-sm text-text-secondary">
            Страница {page + 1} из {Math.ceil(data.total / limit)}
          </span>
          <Button size="sm" variant="secondary" disabled={(page + 1) * limit >= data.total} onClick={() => setPage(page + 1)}>
            Далее →
          </Button>
        </div>
      )}
    </div>
  )
}
