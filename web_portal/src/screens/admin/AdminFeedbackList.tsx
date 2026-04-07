import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Button, Skeleton, Notification } from '@shared/ui'
import { useAdminFeedback } from '@/hooks/useFeedbackQueries'

type StatusFilter = 'all' | 'new' | 'in_progress' | 'resolved' | 'rejected'

const statusLabels: Record<StatusFilter, string> = {
  all: 'Все',
  new: 'Новые',
  in_progress: 'В работе',
  resolved: 'Решённые',
  rejected: 'Отклонённые',
}

export default function AdminFeedbackList() {
  const navigate = useNavigate()
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [page, setPage] = useState(0)
  const limit = 20

  const { data, isLoading, error } = useAdminFeedback({
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
    return <Notification type="danger">Не удалось загрузить обращения.</Notification>
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-display font-bold text-text-primary">Обращения пользователей</h1>
        <p className="text-text-secondary mt-1">Всего: {data.total}</p>
      </div>

      {/* Filter buttons */}
      <div className="flex gap-2 flex-wrap">
        {(['all', 'new', 'in_progress', 'resolved', 'rejected'] as StatusFilter[]).map((status) => (
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

      {/* Feedback list */}
      <div className="space-y-3">
        {data.items.length === 0 ? (
          <Card className="p-8 text-center">
            <p className="text-text-secondary">Обращения не найдены</p>
          </Card>
        ) : (
          data.items.map((feedback) => (
            <Card key={feedback.id} className="p-4">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-sm font-mono text-text-tertiary">#{feedback.id}</span>
                    <span className="text-sm text-text-secondary">
                      {feedback.username ? `@${feedback.username}` : `User #${feedback.user_id}`}
                    </span>
                    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                      feedback.status === 'new' ? 'bg-info-muted text-info' :
                      feedback.status === 'in_progress' ? 'bg-warning-muted text-warning' :
                      feedback.status === 'resolved' ? 'bg-success-muted text-success' :
                      'bg-danger-muted text-danger'
                    }`}>
                      {statusLabels[feedback.status as StatusFilter] ?? feedback.status}
                    </span>
                  </div>
                  <p className="text-sm text-text-primary line-clamp-2">{feedback.text}</p>
                  <p className="text-xs text-text-tertiary mt-2">
                    {new Date(feedback.created_at).toLocaleDateString('ru-RU')}
                  </p>
                </div>
                <Button size="sm" variant="secondary" onClick={() => navigate(`/admin/feedback/${feedback.id}`)}>
                  Просмотр
                </Button>
              </div>
            </Card>
          ))
        )}
      </div>

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
