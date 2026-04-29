import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Card, Button, StatusPill, EmptyState, Skeleton } from '@/components/ui'
import { formatCurrency, formatDate } from '@/lib/formatters'
import { WITHDRAWAL_FEE, formatRatePct } from '@/lib/constants'
import { useMe, usePayouts } from '@/hooks/queries'
import styles from './OwnPayouts.module.css'

const PAYOUT_STATUS_PILL: Record<string, { variant: 'success' | 'warning' | 'danger' | 'info' | 'neutral'; label: string }> = {
  paid:       { variant: 'success', label: 'Выплачено' },
  processing: { variant: 'info',    label: 'В обработке' },
  pending:    { variant: 'warning', label: 'Ожидает' },
  rejected:   { variant: 'danger',  label: 'Отклонено' },
}

// GAP-02: Cooldown timer helper
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
  const { data: payouts = [], isLoading, refetch } = usePayouts()
  
  // GAP-02: Cooldown state
  const [cooldownRemaining, setCooldownRemaining] = useState<number>(0)

  useEffect(() => {
    // Find last payout and check cooldown
    if (payouts.length > 0) {
      const lastPayout = payouts.reduce((latest, p) =>
        new Date(p.created_at) > new Date(latest.created_at) ? p : latest,
        payouts[0]
      )
      const lastPayoutTime = new Date(lastPayout.created_at).getTime()
      const cooldownEnd = lastPayoutTime + 24 * 3600 * 1000
      const now = Date.now()
      const remaining = cooldownEnd - now
      
      if (remaining > 0) {
        const raf = window.requestAnimationFrame(() => setCooldownRemaining(remaining))
        const timer = setInterval(() => {
          setCooldownRemaining(prev => {
            const next = prev - 1000
            return next > 0 ? next : 0
          })
        }, 1000)
        return () => {
          window.cancelAnimationFrame(raf)
          clearInterval(timer)
        }
      } else {
        const raf = window.requestAnimationFrame(() => setCooldownRemaining(0))
        return () => window.cancelAnimationFrame(raf)
      }
    }
  }, [payouts])

  const earnedRub = me?.earned_rub ?? '0.00'
  const isCooldownActive = cooldownRemaining > 0

  return (
    <ScreenShell>
      <Card title="Доступно к выводу">
        <p className={styles.balance}>{formatCurrency(earnedRub)}</p>
        <p className={styles.hint}>Мин. 1 000 ₽ · Комиссия {formatRatePct(WITHDRAWAL_FEE)}</p>
        {isCooldownActive && (
          <p className={styles.cooldown}>
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

      <p className={styles.sectionTitle}>История выплат</p>

      <Button variant="secondary" size="sm" onClick={() => refetch()}>🔄 Обновить</Button>

      {isLoading ? (
        <div className={styles.list}>
          <Skeleton height={80} />
          <Skeleton height={80} />
        </div>
      ) : payouts.length === 0 ? (
        <EmptyState icon="💸" title="Пока нет выплат" />
      ) : (
        <div className={styles.list}>
          {payouts.map((payout) => {
            const pill = PAYOUT_STATUS_PILL[payout.status] ?? { variant: 'neutral' as const, label: payout.status }
            return (
              <Card key={payout.id}>
                <div className={styles.payoutHeader}>
                  <span className={styles.payoutTitle}>Выплата #{payout.id}</span>
                  <StatusPill status={pill.variant} size="sm">{pill.label}</StatusPill>
                </div>
                <div className={styles.payoutDate}>{formatDate(payout.created_at)}</div>
                <div className={styles.payoutDetails}>
                  <div className={styles.detailCell}>
                    <span className={styles.detailLabel}>Запрошено</span>
                    <span className={styles.detailValue}>{formatCurrency(payout.gross_amount)}</span>
                  </div>
                  <div className={styles.detailCell}>
                    <span className={styles.detailLabel}>Получено</span>
                    <span className={styles.detailValueGreen}>{formatCurrency(payout.net_amount)}</span>
                  </div>
                </div>
              </Card>
            )
          })}
        </div>
      )}
    </ScreenShell>
  )
}
