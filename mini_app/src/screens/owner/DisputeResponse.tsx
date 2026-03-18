import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Card, Button, Notification, StatusPill, Skeleton } from '@/components/ui'
import { PUBLICATION_FORMATS, DISPUTE_REASON_LABELS } from '@/lib/constants'
import { formatCurrency } from '@/lib/formatters'
import type { ResolutionAction } from '@/lib/types'
import { useHaptic } from '@/hooks/useHaptic'
import { useDispute, useReplyToDispute } from '@/hooks/queries'
import styles from './DisputeResponse.module.css'

const MIN_REPLY = 20

const RESOLUTION_PILL: Record<ResolutionAction, { variant: 'success' | 'warning' | 'danger' | 'neutral'; label: string }> = {
  full_refund:     { variant: 'success', label: 'Полный возврат' },
  partial_refund:  { variant: 'warning', label: 'Частичный возврат' },
  no_refund:       { variant: 'danger',  label: 'Без возврата' },
  warning:         { variant: 'neutral', label: 'Предупреждение' },
}

export default function DisputeResponse() {
  const { id } = useParams()
  const navigate = useNavigate()
  const haptic = useHaptic()

  const numId = id ? parseInt(id) : null
  const { data: dispute, isLoading } = useDispute(numId)
  const { mutate: replyToDispute, isPending } = useReplyToDispute()

  const [ownerReply, setOwnerReply] = useState('')

  if (isLoading) {
    return (
      <ScreenShell>
        <Skeleton height={60} />
        <Skeleton height={200} />
        <Skeleton height={120} />
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

  const placement = dispute.placement
  const fmt = placement ? PUBLICATION_FORMATS[placement.publication_format] : null

  const handleSubmit = () => {
    haptic.success()
    replyToDispute(
      { id: dispute.id, comment: ownerReply },
      { onSuccess: () => navigate('/own/requests') },
    )
  }

  return (
    <ScreenShell>
      <Notification type="warning">
        <span style={{ fontSize: 'var(--rh-text-sm)' }}>
          ⚠️ У вас открытый спор по заявке #{dispute.placement_id}
        </span>
      </Notification>

      <p className={styles.sectionTitle}>Претензия рекламодателя</p>
      <Card>
        <div className={styles.infoRow}>
          <span className={styles.infoLabel}>Причина</span>
          <span className={styles.infoBold}>{DISPUTE_REASON_LABELS[dispute.reason]}</span>
        </div>
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
              <span className={styles.infoValue}>{formatCurrency(placement.final_price ?? placement.proposed_price)}</span>
            </div>
          </>
        )}

        <div className={styles.divider} />

        <p className={styles.commentHeader}>Комментарий рекламодателя:</p>
        <p className={styles.commentText}>{dispute.advertiser_comment}</p>
      </Card>

      {dispute.status === 'open' && (
        <>
          <p className={styles.sectionTitle}>Ваше объяснение</p>
          <textarea
            className={styles.textarea}
            rows={4}
            placeholder={`Минимум ${MIN_REPLY} символов. Подробное объяснение поможет быстрее разрешить спор.`}
            value={ownerReply}
            onChange={(e) => setOwnerReply(e.target.value)}
          />
          <Notification type="info">
            <span style={{ fontSize: 'var(--rh-text-sm)' }}>
              Подробное и честное объяснение повышает шансы на благоприятное решение
            </span>
          </Notification>
          <Button
            fullWidth
            disabled={ownerReply.length < MIN_REPLY || isPending}
            onClick={handleSubmit}
          >
            {isPending ? '⏳ Отправка...' : '📤 Отправить объяснение'}
          </Button>
        </>
      )}

      {dispute.status === 'owner_reply' && dispute.owner_comment && (
        <>
          <p className={styles.sectionTitle}>Ваш ответ</p>
          <Card>
            <p className={styles.commentText}>{dispute.owner_comment}</p>
          </Card>
          <Notification type="info">
            <span style={{ fontSize: 'var(--rh-text-sm)' }}>Ожидание решения администратора</span>
          </Notification>
        </>
      )}

      {dispute.status === 'resolved' && dispute.resolution && (
        <>
          <p className={styles.sectionTitle}>Решение</p>
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
          <Notification
            type={
              dispute.resolution_action === 'no_refund' || dispute.resolution_action === 'warning'
                ? 'success'
                : 'danger'
            }
          >
            <span style={{ fontSize: 'var(--rh-text-sm)' }}>
              {dispute.resolution_action === 'no_refund'
                ? '✅ Средства сохранены — спор решён в вашу пользу'
                : dispute.resolution_action === 'warning'
                  ? '⚠️ Получено предупреждение'
                  : `❌ ${RESOLUTION_PILL[dispute.resolution_action!].label} — часть средств возвращена рекламодателю`}
            </span>
          </Notification>
        </>
      )}
    </ScreenShell>
  )
}
