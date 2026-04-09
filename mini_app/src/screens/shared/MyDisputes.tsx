import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Card, Skeleton, Text, Notification } from '@/components/ui'
import { DISPUTE_REASON_LABELS } from '@/lib/constants'
import { formatDate } from '@/lib/formatters'
import { useMyDisputes } from '@/hooks/queries'
import type { DisputeStatus } from '@/lib/types'
import { useHaptic } from '@/hooks/useHaptic'
import styles from './MyDisputes.module.css'

const STATUS_PILL: Record<DisputeStatus, { variant: string; label: string; emoji: string }> = {
  open: { variant: 'warning', label: 'Открыт', emoji: '🔴' },
  owner_explained: { variant: 'info', label: 'Владелец ответил', emoji: '🟡' },
  resolved: { variant: 'success', label: 'Решён', emoji: '🟢' },
  closed: { variant: 'neutral', label: 'Закрыт', emoji: '⚪' },
}

const STATUS_FILTERS = [
  { key: 'all', label: 'Все' },
  { key: 'open', label: 'Открытые' },
  { key: 'owner_explained', label: 'Ожидание' },
  { key: 'resolved', label: 'Решённые' },
  { key: 'closed', label: 'Закрытые' },
] as const

export default function MyDisputes() {
  const navigate = useNavigate()
  const haptic = useHaptic()
  const [statusFilter, setStatusFilter] = useState<string>('all')

  const { data: disputes, isLoading } = useMyDisputes(statusFilter, 50, 0)

  if (isLoading) {
    return (
      <ScreenShell>
        <Skeleton height={60} />
        <Skeleton height={200} />
        <Skeleton height={200} />
      </ScreenShell>
    )
  }

  if (!disputes || disputes.length === 0) {
    return (
      <ScreenShell>
        <Notification type="info">
          <Text variant="sm">
            {statusFilter === 'all'
              ? 'У вас пока нет споров'
              : `Нет споров со статусом «${STATUS_FILTERS.find((f) => f.key === statusFilter)?.label}»`}
          </Text>
        </Notification>
        <div className={styles.backSection}>
          <button
            className={styles.backBtn}
            onClick={() => navigate(-1)}
          >
            ← Назад
          </button>
        </div>
      </ScreenShell>
    )
  }

  const handleDisputeClick = (dispute: any) => {
    haptic.tap()
    // Navigate to detail — advertiser or owner based on role
    // For simplicity, navigate to detail screen; the detail screen handles roles
    navigate(`/adv/disputes/${dispute.id}`)
  }

  return (
    <ScreenShell>
      {/* Filters */}
      <div className={styles.filters}>
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.key}
            className={`${styles.filterBtn} ${statusFilter === f.key ? styles.filterActive : ''}`}
            onClick={() => setStatusFilter(f.key)}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Dispute cards */}
      {disputes.map((d) => {
        const pill = STATUS_PILL[d.status]
        const reasonLabel = DISPUTE_REASON_LABELS[d.reason] ?? d.reason

        return (
          <Card key={d.id} onClick={() => handleDisputeClick(d)}>
            <div className={styles.disputeHeader}>
              <span className={styles.disputeId}>#{d.id}</span>
              <span className={`${styles.statusBadge} ${styles[pill.variant]}`}>
                {pill.emoji} {pill.label}
              </span>
            </div>
            <div className={styles.disputeReason}>{reasonLabel}</div>
            <div className={styles.disputeMeta}>
              <span className={styles.metaLabel}>Дата:</span>
              <span className={styles.metaValue}>{formatDate(d.created_at)}</span>
            </div>
            {d.owner_comment && (
              <div className={styles.disputeMeta}>
                <span className={styles.metaLabel}>Ответ:</span>
                <span className={styles.metaValue}>✅ Provided</span>
              </div>
            )}
            {d.resolution_action && (
              <div className={styles.disputeMeta}>
                <span className={styles.metaLabel}>Решение:</span>
                <span className={styles.metaValue}>{d.resolution_action}</span>
              </div>
            )}
          </Card>
        )
      })}
    </ScreenShell>
  )
}
