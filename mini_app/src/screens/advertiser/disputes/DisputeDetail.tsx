import { useParams } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Card, StatusPill, ArbitrationPanel, Timeline, Notification, Skeleton, Text } from '@/components/ui'
import { PUBLICATION_FORMATS, DISPUTE_REASON_LABELS } from '@/lib/constants'
import { formatCurrency, formatDateTime, formatDate } from '@/lib/formatters'
import { useDispute } from '@/hooks/queries'
import type { DisputeStatus, ResolutionAction } from '@/lib/types'
import styles from './DisputeDetail.module.css'

const STATUS_PILL: Record<DisputeStatus, { variant: 'success' | 'warning' | 'danger' | 'info' | 'neutral'; label: string }> = {
  open:              { variant: 'warning', label: 'Ожидает ответа владельца' },
  owner_explained:   { variant: 'info',    label: 'Владелец ответил' },
  resolved:          { variant: 'success', label: 'Решён' },
  closed:            { variant: 'neutral', label: 'Закрыт' },
}

const RESOLUTION_PILL: Record<ResolutionAction, { variant: 'success' | 'warning' | 'danger' | 'neutral'; label: string }> = {
  full_refund:      { variant: 'success', label: 'Полный возврат' },
  partial_refund:   { variant: 'warning', label: 'Частичный возврат' },
  no_refund:        { variant: 'danger',  label: 'Без возврата' },
  warning:          { variant: 'neutral', label: 'Предупреждение' },
  owner_fault:      { variant: 'danger',  label: 'Вина владельца' },
  advertiser_fault: { variant: 'danger',  label: 'Вина рекламодателя' },
  technical:        { variant: 'neutral', label: 'Технический сбой' },
  partial:          { variant: 'warning', label: 'Частичное решение' },
}

export default function DisputeDetail() {
  const { id } = useParams()
  const numId = id ? parseInt(id) : null
  const { data: dispute, isLoading } = useDispute(numId)

  if (isLoading) {
    return (
      <ScreenShell>
        <Skeleton height={120} />
        <Skeleton height={150} />
        <Skeleton height={100} />
      </ScreenShell>
    )
  }

  if (!dispute) {
    return (
      <ScreenShell>
        <Notification type="danger">Спор не найден</Notification>
      </ScreenShell>
    )
  }

  const pill = STATUS_PILL[dispute.status]
  const placement = dispute.placement
  const fmt = placement ? PUBLICATION_FORMATS[placement.publication_format] : null
  const ownerReplyDate = new Date(new Date(dispute.created_at).getTime() + 24 * 60 * 60 * 1000).toISOString()

  const timelineEvents = [
    {
      id: 'opened',
      icon: '📋',
      title: 'Спор открыт',
      subtitle: formatDateTime(dispute.created_at),
      variant: 'success' as const,
    },
    {
      id: 'reply',
      icon: dispute.owner_comment ? '💬' : '⏳',
      title: 'Ответ владельца',
      subtitle: dispute.owner_comment ? formatDateTime(ownerReplyDate) : 'Ожидание...',
      variant: dispute.owner_comment
        ? 'success' as const
        : dispute.status === 'open'
          ? 'warning' as const
          : 'default' as const,
    },
    {
      id: 'resolution',
      icon: dispute.resolution ? '⚖️' : '⏳',
      title: 'Решение администратора',
      subtitle: dispute.resolution && dispute.resolved_at ? formatDateTime(dispute.resolved_at) : 'Ожидание...',
      variant: dispute.resolution ? 'success' as const : 'default' as const,
    },
  ]

  return (
    <ScreenShell>
      <Card title="Статус спора">
        <div className={styles.statusRow}>
          <StatusPill status={pill.variant}>{pill.label}</StatusPill>
        </div>
        <div className={styles.timelineWrapper}>
          <Timeline events={timelineEvents} />
        </div>
      </Card>

      <ArbitrationPanel title="Детали">
        <div className={styles.infoRows}>
          {placement && (
            <>
              <div className={styles.infoRow}>
                <span className={styles.infoLabel}>Канал</span>
                <span className={styles.infoValue}>@{placement.channel?.username ?? `#${placement.channel_id}`}</span>
              </div>
              {fmt && (
                <div className={styles.infoRow}>
                  <span className={styles.infoLabel}>Формат</span>
                  <span className={styles.infoValue}>{fmt.icon} {fmt.name}</span>
                </div>
              )}
              <div className={styles.infoRow}>
                <span className={styles.infoLabel}>Сумма</span>
                <span className={styles.infoValue}>{formatCurrency(placement.final_price ?? placement.counter_price ?? placement.proposed_price)}</span>
              </div>
            </>
          )}
          <div className={styles.infoRow}>
            <span className={styles.infoLabel}>Причина</span>
            <span className={styles.infoValue}>{DISPUTE_REASON_LABELS[dispute.reason]}</span>
          </div>
        </div>
      </ArbitrationPanel>

      <p className={styles.sectionTitle}>Ваша жалоба</p>
      <Card>
        <p className={styles.commentText}>{dispute.advertiser_comment}</p>
      </Card>

      {dispute.owner_comment && (
        <>
          <p className={styles.sectionTitle}>Ответ владельца</p>
          <Card>
            <p className={styles.commentText}>{dispute.owner_comment}</p>
          </Card>
        </>
      )}

      {dispute.status === 'resolved' && dispute.resolution && (
        <>
          <p className={styles.sectionTitle}>Решение администратора</p>
          <Card>
            <p className={styles.commentText}>{dispute.resolution}</p>
            {dispute.resolution_action && (
              <div className={styles.resolutionPill}>
                <StatusPill status={RESOLUTION_PILL[dispute.resolution_action].variant}>
                  {RESOLUTION_PILL[dispute.resolution_action].label}
                </StatusPill>
              </div>
            )}
          </Card>
        </>
      )}

      {(dispute.status === 'open' || dispute.status === 'owner_explained') && (
        <Notification type="info">
          <Text variant="sm">
            Споры рассматриваются в течение 7 дней. Истекает: {formatDate(dispute.expires_at)}
          </Text>
        </Notification>
      )}
    </ScreenShell>
  )
}
