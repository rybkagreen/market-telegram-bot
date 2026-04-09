import React, { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Card, Button, Notification, Skeleton, Text } from '@/components/ui'
import { MIN_DISPUTE_COMMENT, DISPUTE_REASON_LABELS, PUBLICATION_FORMATS } from '@/lib/constants'
import { formatCurrency, formatDateTime } from '@/lib/formatters'
import type { DisputeReason } from '@/lib/types'
import { useHaptic } from '@/hooks/useHaptic'
import { usePlacement, useCreateDispute } from '@/hooks/queries'
import styles from './OpenDispute.module.css'

const DISPUTE_REASONS: { key: DisputeReason; icon: string }[] = [
  { key: 'not_published',  icon: '📭' },
  { key: 'wrong_time',     icon: '⏰' },
  { key: 'wrong_text',     icon: '✏️' },
  { key: 'early_deletion', icon: '🗑' },
  { key: 'other',          icon: '💬' },
]

const DISPUTE_WINDOW_MS = 48 * 60 * 60 * 1000

export default function OpenDispute() {
  const { id } = useParams()
  const navigate = useNavigate()
  const haptic = useHaptic()

  const numId = id ? parseInt(id) : null
  const { data: placement, isLoading } = usePlacement(numId)
  const { mutate: createDispute, isPending } = useCreateDispute()

  const [selectedReason, setSelectedReason] = useState<DisputeReason | null>(null)
  const [comment, setComment] = useState('')

  // Hooks must be called unconditionally at the top level
  const [now, setNow] = React.useState(() => Date.now())

  React.useEffect(() => {
    const interval = setInterval(() => setNow(Date.now()), 60000)
    return () => clearInterval(interval)
  }, [])

  const isInWindow = placement && placement.published_at !== null
    ? now - new Date(placement.published_at).getTime() <= DISPUTE_WINDOW_MS
    : false

  const isPublished = placement?.status === 'published'
  const hasDispute = placement?.has_dispute
  const canOpen = Boolean(isPublished && !hasDispute && isInWindow)

  if (isLoading) {
    return (
      <ScreenShell>
        <Skeleton height={150} />
        <Skeleton height={200} />
      </ScreenShell>
    )
  }

  if (!placement) {
    return (
      <ScreenShell>
        <Notification type="danger">Заявка не найдена</Notification>
      </ScreenShell>
    )
  }

  const handleSubmit = () => {
    if (!selectedReason) return
    haptic.warning()
    createDispute(
      { placement_id: placement.id, reason: selectedReason, comment },
      { onSuccess: (data) => { navigate(`/adv/disputes/${data.id}`) } },
    )
  }

  if (!canOpen) {
    const reason = !isPublished
      ? 'Спор можно открыть только для опубликованных кампаний'
      : hasDispute
        ? 'Спор уже открыт для этой кампании'
        : 'Время для открытия спора истекло (48ч)'

    return (
      <ScreenShell>
        <Notification type="danger">
          <Text variant="sm">❌ {reason}</Text>
        </Notification>
        <div className={styles.backSection}>
          <Button variant="secondary" fullWidth onClick={() => navigate(-1)}>
            Назад
          </Button>
        </div>
      </ScreenShell>
    )
  }

  return (
    <ScreenShell>
      <Card title="Кампания">
        <div className={styles.infoRow}>
          <span className={styles.infoLabel}>Канал</span>
          <span className={styles.infoValue}>@{placement.channel?.username ?? `#${placement.channel_id}`}</span>
        </div>
        <div className={styles.infoRow}>
          <span className={styles.infoLabel}>Формат</span>
          <span className={styles.infoValue}>
            {PUBLICATION_FORMATS[placement.publication_format].icon}{' '}
            {PUBLICATION_FORMATS[placement.publication_format].name}
          </span>
        </div>
        <div className={styles.infoRow}>
          <span className={styles.infoLabel}>Цена</span>
          <span className={styles.infoValue}>{formatCurrency(placement.final_price ?? placement.proposed_price)}</span>
        </div>
        {placement.published_at && (
          <div className={styles.infoRow}>
            <span className={styles.infoLabel}>Опубликовано</span>
            <span className={styles.infoValue}>{formatDateTime(placement.published_at)}</span>
          </div>
        )}
      </Card>

      <p className={styles.sectionTitle}>Причина спора</p>

      <div className={styles.reasons}>
        {DISPUTE_REASONS.map(({ key, icon }) => (
          <button
            key={key}
            className={`${styles.reasonBtn} ${selectedReason === key ? styles.reasonSelected : ''}`}
            onClick={() => setSelectedReason(key)}
          >
            <span className={styles.reasonIcon}>{icon}</span>
            <span className={styles.reasonLabel}>{DISPUTE_REASON_LABELS[key]}</span>
          </button>
        ))}
      </div>

      <label className={styles.label}>Опишите проблему подробно</label>
      <textarea
        className={styles.textarea}
        rows={4}
        placeholder={`Минимум ${MIN_DISPUTE_COMMENT} символов. Подробное описание поможет быстрее разрешить спор.`}
        value={comment}
        onChange={(e) => setComment(e.target.value)}
      />
      <p className={styles.charHint}>{comment.length} / мин. {MIN_DISPUTE_COMMENT}</p>

      <Notification type="warning">
        <Text variant="sm">
          ⚠️ Необоснованные споры могут повлиять на вашу репутацию
        </Text>
      </Notification>

      <Button
        variant="danger"
        fullWidth
        disabled={!selectedReason || comment.length < MIN_DISPUTE_COMMENT || isPending}
        onClick={handleSubmit}
      >
        {isPending ? '⏳ Открытие спора...' : '⚠️ Открыть спор'}
      </Button>
    </ScreenShell>
  )
}
