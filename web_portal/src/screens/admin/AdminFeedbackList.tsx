import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Button,
  Skeleton,
  Notification,
  Icon,
  ScreenHeader,
  EmptyState,
} from '@shared/ui'
import type { IconName } from '@shared/ui'
import { formatDateTimeMSK } from '@/lib/constants'
import { useAdminFeedback } from '@/hooks/useFeedbackQueries'

type StatusFilter = 'all' | 'new' | 'in_progress' | 'resolved' | 'rejected'

const FILTERS: { key: StatusFilter; label: string }[] = [
  { key: 'new', label: 'Новые' },
  { key: 'in_progress', label: 'В работе' },
  { key: 'resolved', label: 'Решённые' },
  { key: 'rejected', label: 'Отклонённые' },
  { key: 'all', label: 'Все' },
]

type Tone = 'info' | 'warning' | 'success' | 'danger' | 'neutral'

const STATUS_META: Record<string, { label: string; tone: Tone; icon: IconName }> = {
  new: { label: 'Новое', tone: 'info', icon: 'pending' },
  in_progress: { label: 'В работе', tone: 'warning', icon: 'hourglass' },
  resolved: { label: 'Решено', tone: 'success', icon: 'verified' },
  rejected: { label: 'Отклонено', tone: 'danger', icon: 'close' },
}

const toneClasses: Record<Tone, string> = {
  info: 'bg-info-muted text-info',
  warning: 'bg-warning-muted text-warning',
  success: 'bg-success-muted text-success',
  danger: 'bg-danger-muted text-danger',
  neutral: 'bg-harbor-elevated text-text-tertiary',
}

export default function AdminFeedbackList() {
  const navigate = useNavigate()
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('new')
  const [page, setPage] = useState(0)
  const limit = 20

  const { data, isLoading, error } = useAdminFeedback({
    status: statusFilter === 'all' ? undefined : statusFilter,
    limit,
    offset: page * limit,
  })

  if (isLoading) {
    return (
      <div className="max-w-[1280px] mx-auto space-y-4">
        <Skeleton className="h-16" />
        <Skeleton className="h-96" />
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="max-w-[1280px] mx-auto">
        <Notification type="danger">Не удалось загрузить обращения.</Notification>
      </div>
    )
  }

  return (
    <div className="max-w-[1280px] mx-auto">
      <ScreenHeader
        crumbs={['Администратор', 'Обращения']}
        title="Обращения пользователей"
        subtitle={`Всего: ${data.total} · ответьте на новые в течение 48 часов`}
      />

      <div className="bg-harbor-card border border-border rounded-xl p-3.5 mb-3.5 flex items-center gap-3 flex-wrap">
        <div className="flex gap-1.5 flex-wrap">
          {FILTERS.map((f) => {
            const on = statusFilter === f.key
            return (
              <button
                key={f.key}
                type="button"
                onClick={() => {
                  setStatusFilter(f.key)
                  setPage(0)
                }}
                className={`inline-flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded-2xl border transition-all ${
                  on
                    ? 'border-accent bg-accent-muted text-accent'
                    : 'border-border bg-transparent text-text-secondary hover:border-border-active'
                }`}
              >
                {f.label}
              </button>
            )
          })}
        </div>
      </div>

      {data.items.length === 0 ? (
        <EmptyState
          icon="feedback"
          title="Обращения не найдены"
          description="Нет записей с выбранным фильтром."
        />
      ) : (
        <div className="space-y-3">
          {data.items.map((feedback) => {
            const meta =
              STATUS_META[feedback.status] ?? { label: feedback.status, tone: 'neutral' as Tone, icon: 'info' as IconName }
            return (
              <button
                key={feedback.id}
                type="button"
                onClick={() => navigate(`/admin/feedback/${feedback.id}`)}
                className="w-full text-left bg-harbor-card border border-border rounded-xl p-5 hover:border-accent/35 transition-colors"
              >
                <div className="flex items-start justify-between gap-4 flex-wrap">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2 flex-wrap">
                      <span className="font-mono text-[11px] text-text-tertiary py-px px-1.5 rounded bg-harbor-elevated">
                        #{feedback.id}
                      </span>
                      <span className="text-[13px] text-text-secondary">
                        {feedback.username ? `@${feedback.username}` : `User #${feedback.user_id}`}
                      </span>
                      <span
                        className={`inline-flex items-center gap-1.5 text-[10.5px] font-bold tracking-[0.08em] uppercase py-0.5 px-1.5 rounded ${toneClasses[meta.tone]}`}
                      >
                        <Icon name={meta.icon} size={11} />
                        {meta.label}
                      </span>
                    </div>
                    <p className="text-[13.5px] text-text-primary line-clamp-2">
                      {feedback.text}
                    </p>
                    <p className="text-[11.5px] text-text-tertiary mt-2 tabular-nums">
                      {formatDateTimeMSK(feedback.created_at)} МСК
                    </p>
                  </div>
                  <Icon name="chevron-right" size={14} className="text-text-tertiary flex-shrink-0 mt-2" />
                </div>
              </button>
            )
          })}
        </div>
      )}

      {data.total > limit && (
        <div className="flex items-center justify-between mt-5 py-3.5 px-[18px] rounded-[10px] border border-border bg-harbor-card">
          <Button
            size="sm"
            variant="ghost"
            iconLeft="arrow-left"
            disabled={page === 0}
            onClick={() => setPage(page - 1)}
          >
            Назад
          </Button>
          <div className="flex items-center gap-2.5 text-[12.5px] text-text-secondary">
            <span>Страница</span>
            <span className="font-mono font-semibold text-text-primary py-0.5 px-2.5 rounded-md bg-harbor-elevated border border-border">
              {page + 1}
            </span>
            <span>из {Math.ceil(data.total / limit)}</span>
          </div>
          <Button
            size="sm"
            variant="ghost"
            iconRight="arrow-right"
            disabled={(page + 1) * limit >= data.total}
            onClick={() => setPage(page + 1)}
          >
            Вперёд
          </Button>
        </div>
      )}
    </div>
  )
}
