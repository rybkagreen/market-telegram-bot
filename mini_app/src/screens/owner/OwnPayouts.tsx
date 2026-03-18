import { useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Card, Button, StatusPill, EmptyState, Skeleton } from '@/components/ui'
import { formatCurrency, formatDate } from '@/lib/formatters'
import { useMe, usePayouts } from '@/hooks/queries'
import styles from './OwnPayouts.module.css'

const PAYOUT_STATUS_PILL: Record<string, { variant: 'success' | 'warning' | 'danger' | 'info' | 'neutral'; label: string }> = {
  paid:       { variant: 'success', label: 'Выплачено' },
  processing: { variant: 'info',    label: 'В обработке' },
  pending:    { variant: 'warning', label: 'Ожидает' },
  rejected:   { variant: 'danger',  label: 'Отклонено' },
}

export default function OwnPayouts() {
  const navigate = useNavigate()
  const { data: me } = useMe()
  const { data: payouts = [], isLoading, refetch } = usePayouts()

  const earnedRub = me?.earned_rub ?? '0.00'

  return (
    <ScreenShell>
      <Card title="Доступно к выводу">
        <p className={styles.balance}>{formatCurrency(earnedRub)}</p>
        <p className={styles.hint}>Мин. 1 000 ₽ · Комиссия 1,5%</p>
      </Card>

      <Button fullWidth onClick={() => navigate('/own/payouts/request')}>
        💸 Запросить вывод
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
                    <span className={styles.detailValue}>{formatCurrency(payout.amount)}</span>
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
