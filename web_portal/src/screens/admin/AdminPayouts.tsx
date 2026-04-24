import { useState } from 'react'
import {
  Button,
  Skeleton,
  Notification,
  Icon,
  ScreenHeader,
  EmptyState,
} from '@shared/ui'
import type { IconName } from '@shared/ui'
import { formatCurrency, formatDateTimeMSK } from '@/lib/constants'
import {
  useAdminPayouts,
  useApproveAdminPayout,
  useRejectAdminPayout,
} from '@/hooks/useAdminQueries'

type StatusFilter = 'all' | 'pending' | 'processing' | 'paid' | 'rejected'

const FILTERS: { key: StatusFilter; label: string }[] = [
  { key: 'pending', label: 'Ожидают' },
  { key: 'processing', label: 'В обработке' },
  { key: 'paid', label: 'Выплачены' },
  { key: 'rejected', label: 'Отклонены' },
  { key: 'all', label: 'Все' },
]

type Tone = 'success' | 'warning' | 'danger' | 'neutral'

const STATUS_META: Record<string, { label: string; tone: Tone; icon: IconName }> = {
  pending: { label: 'Ожидает', tone: 'warning', icon: 'hourglass' },
  processing: { label: 'В обработке', tone: 'warning', icon: 'clock' },
  paid: { label: 'Выплачено', tone: 'success', icon: 'check' },
  rejected: { label: 'Отклонено', tone: 'danger', icon: 'close' },
}

const toneClasses: Record<Tone, string> = {
  success: 'bg-success-muted text-success',
  warning: 'bg-warning-muted text-warning',
  danger: 'bg-danger-muted text-danger',
  neutral: 'bg-harbor-elevated text-text-tertiary',
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
      <div className="max-w-[1280px] mx-auto space-y-4">
        <Skeleton className="h-16" />
        <Skeleton className="h-96" />
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="max-w-[1280px] mx-auto">
        <Notification type="danger">Не удалось загрузить список выплат.</Notification>
      </div>
    )
  }

  return (
    <div className="max-w-[1280px] mx-auto">
      <ScreenHeader
        title="Заявки на выплату"
        subtitle={`Всего: ${data.total} · одобряйте вручную перед переводом банку`}
      />

      {successMessage && (
        <div className="mb-4">
          <Notification type="success">{successMessage}</Notification>
        </div>
      )}

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
          icon="payouts"
          title="Нет заявок"
          description="В выбранном фильтре нет записей."
        />
      ) : (
        <div className="space-y-3">
          {data.items.map((payout) => {
            const meta =
              STATUS_META[payout.status] ??
              { label: payout.status, tone: 'neutral' as Tone, icon: 'info' as IconName }
            return (
              <div
                key={payout.id}
                className="bg-harbor-card border border-border rounded-xl p-5"
              >
                <div className="flex items-start justify-between gap-4 flex-wrap">
                  <div className="flex-1 min-w-[220px] md:min-w-[320px]">
                    <div className="flex items-center gap-2 mb-3 flex-wrap">
                      <span
                        className={`inline-flex items-center gap-1.5 text-[10.5px] font-bold tracking-[0.08em] uppercase py-1 px-2 rounded ${toneClasses[meta.tone]}`}
                      >
                        <Icon name={meta.icon} size={12} />
                        {meta.label}
                      </span>
                      <span className="font-mono text-[11px] text-text-tertiary py-px px-1.5 rounded bg-harbor-elevated">
                        #{payout.id}
                      </span>
                      <span className="text-[12px] text-text-tertiary">
                        Владелец #{payout.owner_id}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 mb-3">
                      <StatCell label="Запрошено" value={formatCurrency(payout.gross_amount)} />
                      <StatCell
                        label="Комиссия"
                        value={formatCurrency(payout.fee_amount)}
                        tone="danger"
                      />
                      <StatCell
                        label="К выплате"
                        value={formatCurrency(payout.net_amount)}
                        tone="success"
                      />
                    </div>

                    <div className="text-[12.5px] text-text-secondary font-mono truncate max-w-lg">
                      <Icon name="bank" size={12} className="inline -mt-0.5 mr-1.5 text-text-tertiary" />
                      {payout.requisites}
                    </div>
                    <div className="text-[11.5px] text-text-tertiary mt-1 tabular-nums">
                      {formatDateTimeMSK(payout.created_at)} МСК
                    </div>
                  </div>

                  {payout.status === 'pending' && (
                    <div className="flex gap-2 flex-shrink-0">
                      <Button
                        size="sm"
                        variant="primary"
                        iconLeft="check"
                        disabled={approveMutation.isPending}
                        loading={approveMutation.isPending}
                        onClick={() => handleApprove(payout.id)}
                      >
                        Одобрить
                      </Button>
                      <Button
                        size="sm"
                        variant="danger"
                        iconLeft="close"
                        disabled={rejectMutation.isPending}
                        onClick={() => setRejectingId(payout.id)}
                      >
                        Отклонить
                      </Button>
                    </div>
                  )}
                </div>

                {rejectingId === payout.id && (
                  <div className="mt-3 bg-harbor-secondary border border-danger/20 rounded-lg p-3 flex gap-2 items-center flex-wrap">
                    <input
                      type="text"
                      placeholder="Причина отклонения…"
                      className="flex-1 min-w-[180px] md:min-w-[240px] px-3 py-2 min-h-11 bg-harbor-elevated border border-border rounded-md text-sm text-text-primary placeholder:text-text-tertiary focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/25"
                      value={rejectReason}
                      onChange={(e) => setRejectReason(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleRejectSubmit(payout.id)
                      }}
                    />
                    <Button
                      size="sm"
                      variant="danger"
                      iconLeft="check"
                      disabled={!rejectReason.trim() || rejectMutation.isPending}
                      loading={rejectMutation.isPending}
                      onClick={() => handleRejectSubmit(payout.id)}
                    >
                      Подтвердить
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
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

function StatCell({
  label,
  value,
  tone,
}: {
  label: string
  value: string
  tone?: 'success' | 'danger'
}) {
  const color = tone === 'success' ? 'text-success' : tone === 'danger' ? 'text-danger' : 'text-text-primary'
  return (
    <div className="bg-harbor-secondary rounded-md p-2">
      <div className="text-[10px] uppercase tracking-wider text-text-tertiary">{label}</div>
      <div className={`font-mono tabular-nums font-semibold text-[14px] ${color}`}>{value}</div>
    </div>
  )
}
