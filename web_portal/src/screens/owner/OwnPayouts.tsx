import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Button, StatusPill, EmptyState, Skeleton } from '@shared/ui'
import { formatCurrency, formatDateMSK } from '@/lib/constants'
import { useMe } from '@/hooks/queries'
import { useMyPayouts } from '@/hooks/usePayoutQueries'

const COOLDOWN_HOURS = 24

const PAYOUT_STATUS_PILL: Record<string, { variant: 'success' | 'warning' | 'danger' | 'default'; label: string }> = {
  paid: { variant: 'success', label: 'Выплачено' },
  processing: { variant: 'warning', label: 'В обработке' },
  pending: { variant: 'warning', label: 'Ожидает' },
  rejected: { variant: 'danger', label: 'Отклонено' },
  cancelled: { variant: 'default', label: 'Отменено' },
}

function formatCountdown(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000)
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

export default function OwnPayouts() {
  const navigate = useNavigate()
  const { data: me } = useMe()
  const { data: payouts = [], isLoading, refetch } = useMyPayouts()

  const [cooldownRemaining, setCooldownRemaining] = useState(0)

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (payouts.length === 0) return
    const lastPayout = payouts.reduce((latest, p) =>
      new Date(p.created_at) > new Date(latest.created_at) ? p : latest,
      payouts[0],
    )
    const cooldownEnd = new Date(lastPayout.created_at).getTime() + COOLDOWN_HOURS * 3600 * 1000
    const remaining = cooldownEnd - Date.now()

    if (remaining > 0) {
      setCooldownRemaining(remaining)
      const timer = setInterval(() => {
        setCooldownRemaining((prev) => {
          const next = prev - 1000
          return next > 0 ? next : 0
        })
      }, 1000)
      return () => clearInterval(timer)
    } else {
      setCooldownRemaining(0)
    }
  }, [payouts])
  /* eslint-enable react-hooks/set-state-in-effect */

  const earnedRub = me?.earned_rub ?? '0'
  const isCooldownActive = cooldownRemaining > 0

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-display font-bold text-text-primary">Выплаты</h1>

      {/* Balance */}
      <Card title="Доступно к выводу">
        <p className="text-3xl font-bold text-success">{formatCurrency(earnedRub)}</p>
        <p className="text-sm text-text-tertiary mt-1">Мин. 1 000 ₽ · Комиссия 1,5%</p>
        {isCooldownActive && (
          <p className="text-sm text-warning mt-2">
            ⏱ Следующая выплата через <strong>{formatCountdown(cooldownRemaining)}</strong>
          </p>
        )}
      </Card>

      <Button
        fullWidth
        disabled={isCooldownActive}
        onClick={() => navigate('/own/payouts/request')}
      >
        {isCooldownActive ? '🔒 Вывод временно недоступен' : '💸 Запросить вывод'}
      </Button>

      {/* History */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-text-primary">История выплат</h2>
        <Button variant="ghost" size="sm" onClick={() => void refetch()}>🔄</Button>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-20" />
          <Skeleton className="h-20" />
        </div>
      ) : payouts.length === 0 ? (
        <EmptyState icon="💸" title="Пока нет выплат" />
      ) : (
        <div className="space-y-3">
          {payouts.map((payout) => {
            const pill = PAYOUT_STATUS_PILL[payout.status] ?? { variant: 'default' as const, label: payout.status }
            return (
              <Card key={payout.id} className="p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-semibold text-text-primary">Выплата #{payout.id}</span>
                  <StatusPill status={pill.variant}>{pill.label}</StatusPill>
                </div>
                <p className="text-xs text-text-tertiary mb-3">
                  {formatDateMSK(payout.created_at)}
                </p>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <span className="text-text-tertiary">Запрошено</span>
                    <p className="font-mono text-text-primary">{formatCurrency(payout.gross_amount)}</p>
                  </div>
                  <div>
                    <span className="text-text-tertiary">Получено</span>
                    <p className="font-mono text-success">{formatCurrency(payout.net_amount)}</p>
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
