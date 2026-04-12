import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Button, Skeleton, Notification } from '@shared/ui'
import { formatCurrency, formatDateTimeMSK } from '@/lib/constants'
import { useTransactionHistory } from '@/hooks/useBillingQueries'

const TX_META: Record<string, { label: string; icon: string; incoming: boolean }> = {
  topup: { label: 'Пополнение баланса', icon: '💳', incoming: true },
  escrow_freeze: { label: 'Оплата эскроу', icon: '🔒', incoming: false },
  escrow_release: { label: 'Получение выплаты', icon: '✅', incoming: true },
  payout: { label: 'Вывод средств', icon: '💸', incoming: false },
  payout_fee: { label: 'Комиссия за вывод', icon: '📋', incoming: false },
  refund_full: { label: 'Возврат средств', icon: '↩️', incoming: true },
  adjustment: { label: 'Корректировка', icon: '📝', incoming: true },
}

const STATUS_LABEL: Record<string, string> = {
  completed: 'Выполнено',
  succeeded: 'Выполнено',
  pending: 'В обработке',
  canceled: 'Отменено',
  failed: 'Ошибка',
}

function formatDate(iso: string): string {
  return formatDateTimeMSK(iso)
}

function formatAmount(amount: number, incoming: boolean): string {
  const sign = incoming ? '+' : '−'
  return `${sign}${formatCurrency(amount)}`
}

export default function TransactionHistory() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const { data, isLoading, isError, refetch } = useTransactionHistory(page)

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-20" />
        <Skeleton className="h-20" />
        <Skeleton className="h-20" />
      </div>
    )
  }

  if (isError || !data) {
    return (
      <div className="space-y-4">
        <Notification type="danger">Не удалось загрузить историю</Notification>
        <Button variant="secondary" fullWidth onClick={() => refetch()}>Повторить</Button>
      </div>
    )
  }

  if (data.items.length === 0) {
    return <Notification type="info">Транзакций пока нет</Notification>
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-display font-bold text-text-primary">История транзакций</h1>

      <div className="space-y-3">
        {data.items.map((item) => {
          const meta = TX_META[item.type] ?? { label: item.type, icon: '📄', incoming: true }
          const statusText = STATUS_LABEL[item.status] ?? item.status
          return (
            <Card key={item.id} className="p-4">
              <div className="flex items-start gap-3">
                <span className="text-xl shrink-0">{meta.icon}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-text-primary">{meta.label}</p>
                  {item.description && <p className="text-xs text-text-tertiary mt-0.5">{item.description}</p>}
                  <p className="text-xs text-text-tertiary mt-1">
                    {formatDate(item.created_at)}
                    {item.placement_request_id && ` · заявка #${item.placement_request_id}`}
                  </p>
                </div>
                <div className="text-right shrink-0">
                  <p className={`text-sm font-semibold tabular-nums ${meta.incoming ? 'text-success' : 'text-danger'}`}>
                    {formatAmount(Number(item.amount), meta.incoming)}
                  </p>
                  <p className={`text-xs mt-0.5 ${item.status === 'pending' ? 'text-warning' : 'text-text-tertiary'}`}>
                    {statusText}
                  </p>
                </div>
              </div>
            </Card>
          )
        })}
      </div>

      {data.pages > 1 && (
        <div className="flex items-center justify-between">
          <Button size="sm" variant="secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>← Назад</Button>
          <span className="text-sm text-text-secondary">Страница {page} из {data.pages}</span>
          <Button size="sm" variant="secondary" disabled={page >= data.pages} onClick={() => setPage((p) => p + 1)}>Вперёд →</Button>
        </div>
      )}

      <Button variant="secondary" fullWidth onClick={() => navigate('/cabinet')}>← Назад в кабинет</Button>
    </div>
  )
}
