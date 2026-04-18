import { useState } from 'react'
import { Card, Button, Skeleton, Notification, StatusBadge } from '@shared/ui'
import { formatDateMSK } from '@/lib/constants'
import { useAdminPayouts, useApproveAdminPayout, useRejectAdminPayout } from '@/hooks/useAdminQueries'

type StatusFilter = 'all' | 'pending' | 'processing' | 'paid' | 'rejected'

const statusLabels: Record<StatusFilter, string> = {
  all: 'Все',
  pending: 'Ожидают',
  processing: 'В обработке',
  paid: 'Выплачены',
  rejected: 'Отклонены',
}

export default function AdminPayouts() {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('pending')
  const [page, setPage] = useState(0)
  const [rejectingId, setRejectingId] = useState<number | null>(null)
  const [rejectReason, setRejectReason] = useState('')
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  const limit = 20
  const { data, isLoading, error } = useAdminPayouts({
    status: statusFilter === 'all' ? undefined : statusFilter,
    limit,
    offset: page * limit,
  })

  const approveMutation = useApproveAdminPayout()
  const rejectMutation = useRejectAdminPayout()

  const handleApprove = (payoutId: number) => {
    approveMutation.mutate(payoutId, {
      onSuccess: () => {
        setSuccessMessage('Выплата одобрена')
        setTimeout(() => setSuccessMessage(null), 3000)
      },
    })
  }

  const handleRejectSubmit = (payoutId: number) => {
    if (!rejectReason.trim()) return
    rejectMutation.mutate(
      { payoutId, reason: rejectReason },
      {
        onSuccess: () => {
          setSuccessMessage('Выплата отклонена')
          setRejectingId(null)
          setRejectReason('')
          setTimeout(() => setSuccessMessage(null), 3000)
        },
      },
    )
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-12" />
        <Skeleton className="h-96" />
      </div>
    )
  }

  if (error || !data) {
    return <Notification type="danger">Не удалось загрузить список выплат.</Notification>
  }

  return (
    <div className="space-y-6">
      {/* Success message */}
      {successMessage && (
        <Notification type="success">{successMessage}</Notification>
      )}

      {/* Header */}
      <div>
        <h1 className="text-2xl font-display font-bold text-text-primary">Заявки на выплату</h1>
        <p className="text-text-secondary mt-1">Всего: {data.total}</p>
      </div>

      {/* Filter buttons */}
      <div className="flex gap-2 flex-wrap">
        {(['all', 'pending', 'processing', 'paid', 'rejected'] as StatusFilter[]).map((status) => (
          <button
            key={status}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              statusFilter === status
                ? 'bg-accent text-accent-text'
                : 'bg-harbor-elevated text-text-secondary hover:text-text-primary'
            }`}
            onClick={() => {
              setStatusFilter(status)
              setPage(0)
            }}
          >
            {statusLabels[status]}
          </button>
        ))}
      </div>

      {/* Payouts list */}
      <Card className="p-0 overflow-hidden">
        {data.items.length === 0 ? (
          <div className="px-5 py-8 text-center text-text-secondary">Нет ожидающих заявок</div>
        ) : (
          <div className="divide-y divide-border">
            {data.items.map((payout) => (
              <div key={payout.id} className="px-5 py-4">
                <div className="flex items-start justify-between gap-4 mb-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-sm font-mono text-text-tertiary">#{payout.id}</span>
                      <StatusBadge status={payout.status} />
                    </div>
                    <div className="grid grid-cols-2 gap-4 text-sm mb-2">
                      <div>
                        <p className="text-text-tertiary">Владелец ID</p>
                        <p className="text-text-primary font-mono">#{payout.owner_id}</p>
                      </div>
                      <div>
                        <p className="text-text-tertiary">Сумма (нетто)</p>
                        <p className="text-text-primary font-mono">{payout.net_amount} ₽</p>
                      </div>
                      <div>
                        <p className="text-text-tertiary">Комиссия</p>
                        <p className="text-text-primary font-mono">{payout.fee_amount} ₽</p>
                      </div>
                      <div>
                        <p className="text-text-tertiary">Всего</p>
                        <p className="text-text-primary font-mono">{payout.gross_amount} ₽</p>
                      </div>
                    </div>
                    <div className="mb-2">
                      <p className="text-text-tertiary text-xs">Реквизиты</p>
                      <p className="text-text-primary text-sm font-mono truncate max-w-xs">{payout.requisites}</p>
                    </div>
                    <p className="text-xs text-text-tertiary">{formatDateMSK(payout.created_at)}</p>
                  </div>
                  {payout.status === 'pending' && (
                    <div className="flex gap-2 shrink-0">
                      <Button
                        size="sm"
                        variant="primary"
                        disabled={approveMutation.isPending}
                        onClick={() => handleApprove(payout.id)}
                      >
                        Одобрить
                      </Button>
                      <Button
                        size="sm"
                        variant="secondary"
                        disabled={rejectMutation.isPending}
                        onClick={() => setRejectingId(payout.id)}
                      >
                        Отклонить
                      </Button>
                    </div>
                  )}
                </div>

                {/* Reject reason input */}
                {rejectingId === payout.id && (
                  <div className="bg-harbor-elevated/50 rounded p-3 flex gap-2 items-end">
                    <input
                      type="text"
                      placeholder="Причина отклонения..."
                      className="flex-1 px-3 py-2 bg-harbor-elevated rounded text-sm text-text-primary placeholder-text-tertiary outline-none"
                      value={rejectReason}
                      onChange={(e) => setRejectReason(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleRejectSubmit(payout.id)
                      }}
                    />
                    <Button
                      size="sm"
                      variant="primary"
                      disabled={!rejectReason.trim() || rejectMutation.isPending}
                      onClick={() => handleRejectSubmit(payout.id)}
                    >
                      Подтвердить
                    </Button>
                    <Button
                      size="sm"
                      variant="secondary"
                      disabled={rejectMutation.isPending}
                      onClick={() => {
                        setRejectingId(null)
                        setRejectReason('')
                      }}
                    >
                      Отмена
                    </Button>
                  </div>
                )}
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
          <Button
            size="sm"
            variant="secondary"
            disabled={(page + 1) * limit >= data.total}
            onClick={() => setPage(page + 1)}
          >
            Далее →
          </Button>
        </div>
      )}
    </div>
  )
}
