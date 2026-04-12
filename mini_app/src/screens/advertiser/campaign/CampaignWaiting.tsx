import { useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Notification, Card, Timeline, ArbitrationPanel, Button, Skeleton } from '@/components/ui'
import { PUBLICATION_FORMATS, formatDateTimeMSK } from '@/lib/constants'
import { formatCurrency } from '@/lib/formatters'
import { useHaptic } from '@/hooks/useHaptic'
import { usePlacement, useUpdatePlacement } from '@/hooks/queries'
import styles from './CampaignWaiting.module.css'

type Variant = 'success' | 'warning' | 'default'
type TimelineEvent = { id: string; icon: string; title: string; subtitle: string; variant: Variant }

/** Format duration in Russian for display in timeline subtitles. */
function formatDurationHours(hours: number): string {
  if (hours <= 24) return `${hours} ч`
  const days = Math.floor(hours / 24)
  const remainingHours = hours % 24
  if (remainingHours === 0) return `${days} дн.`
  return `${days} дн. ${remainingHours} ч`
}

/** Calculate remaining time until scheduled deletion. Returns null if not applicable. */
function calcDeletionRemaining(
  scheduledDeleteAt: string | null | undefined,
  publishedAt: string | null | undefined,
  publicationFormat: string,
): { remainingMs: number; totalMs: number; remainingText: string } | null {
  const now = Date.now()
  let deleteTime: number

  if (scheduledDeleteAt) {
    deleteTime = new Date(scheduledDeleteAt).getTime()
  } else if (publishedAt) {
    const formatInfo = PUBLICATION_FORMATS[publicationFormat as keyof typeof PUBLICATION_FORMATS]
    if (!formatInfo) return null
    const durationSeconds = formatInfo.multiplier === 1.0 ? 86400
      : formatInfo.multiplier === 1.4 ? 172800
      : formatInfo.multiplier === 2.0 ? 604800
      : formatInfo.multiplier === 3.0 ? 86400
      : formatInfo.multiplier === 4.0 ? 172800
      : 86400
    deleteTime = new Date(publishedAt).getTime() + durationSeconds * 1000
  } else {
    return null
  }

  const remainingMs = deleteTime - now
  if (remainingMs <= 0) return null

  const publishedTime = publishedAt ? new Date(publishedAt).getTime() : now
  const totalMs = deleteTime - publishedTime

  // Human-readable remaining time
  const remainingHours = remainingMs / (1000 * 60 * 60)
  let remainingText: string
  if (remainingHours < 1) {
    const mins = Math.ceil(remainingMs / (1000 * 60))
    remainingText = `${mins} мин.`
  } else if (remainingHours < 24) {
    remainingText = `${Math.ceil(remainingHours)} ч`
  } else {
    const days = Math.floor(remainingHours / 24)
    const hours = Math.ceil(remainingHours % 24)
    remainingText = hours > 0 ? `${days} дн. ${hours} ч` : `${days} дн.`
  }

  return { remainingMs, totalMs, remainingText }
}

/** Redirect only for transitions to fundamentally different screens (payment, published). */
function getRedirectPath(id: number, status: string): string | null {
  if (status === 'pending_payment' || status === 'counter_offer') return `/adv/campaigns/${id}/payment`
  if (status === 'published') return `/adv/campaigns/${id}/published`
  // Terminal states (cancelled/failed/refunded/completed) should stay here — this screen shows their details
  return null
}

function buildTimelineEvents(
  placement: {
    status: string
    created_at: string
    expires_at: string
    published_at?: string | null
    scheduled_delete_at?: string | null
    deleted_at?: string | null
    final_schedule?: string | null
    proposed_schedule?: string | null
    rejection_reason?: string | null
    publication_format: string
    erid?: string | null
  },
  isExpired: boolean,
  isTerminal: boolean,
): TimelineEvent[] {
  const st = placement.status

  // Determine which stages are complete based on current status
  const isPastOwner = ['pending_payment', 'escrow', 'published', 'completed'].includes(st)
  const isPastPayment = ['escrow', 'published', 'completed'].includes(st)
  const isPastEscrow = ['published', 'completed'].includes(st)
  const isPublished = st === 'published'
  const isCompleted = st === 'completed'
  const isWaitingPlacement = st === 'escrow' && !isPublished && !isCompleted

  // Terminal state events (cancelled, failed, refunded, failed_permissions)
  if (isTerminal && !isCompleted) {
    const termIcon = st === 'cancelled' ? '🚫' : st === 'refunded' ? '💸' : '⚠️'
    const termTitle = st === 'cancelled' ? 'Отменено' : st === 'refunded' ? 'Возврат средств' : st === 'failed' ? 'Ошибка публикации' : 'Нет прав у бота'
    const termSubtitle = placement.rejection_reason || ''
    return [
      { id: 'created', icon: '✅', title: 'Заявка создана', subtitle: formatDateTimeMSK(placement.created_at), variant: 'success' },
      { id: 'terminal', icon: termIcon, title: termTitle, subtitle: termSubtitle, variant: 'warning' },
    ]
  }

  const events: TimelineEvent[] = []

  // Stage 1: Created (always shown)
  events.push({
    id: 'created',
    icon: '✅',
    title: 'Заявка создана',
    subtitle: formatDateTimeMSK(placement.created_at),
    variant: 'success',
  })

  // Stage 2: Waiting for owner response
  const ownerWaiting = !isPastOwner && !isExpired && !isTerminal
  events.push({
    id: 'waiting_owner',
    icon: isPastOwner ? '✅' : isExpired ? '⏰' : '⏳',
    title: isPastOwner ? 'Владелец принял' : isExpired ? 'Срок ответа истёк' : 'Ожидает ответа владельца',
    subtitle: isPastOwner ? '' : ownerWaiting ? `До ${formatDateTimeMSK(placement.expires_at)} (24 ч)` : '',
    variant: isPastOwner ? 'success' : isExpired ? 'default' : 'warning',
  })

  // Stage 3: Payment
  events.push({
    id: 'payment',
    icon: isPastPayment ? '✅' : '💳',
    title: isPastPayment ? 'Оплачено' : 'Оплата',
    subtitle: isPastPayment ? '' : 'После подтверждения',
    variant: isPastPayment ? 'success' : 'default',
  })

  // Stage 4: Escrow
  events.push({
    id: 'escrow',
    icon: isPastEscrow ? '✅' : '🔒',
    title: isPastEscrow ? 'Эскроу активен' : 'Эскроу',
    subtitle: isPastEscrow ? 'Средства заблокированы' : '',
    variant: isPastEscrow ? 'success' : 'default',
  })

  // Stage 5: Waiting for placement (after escrow, before published)
  if (isWaitingPlacement) {
    const formatInfo = PUBLICATION_FORMATS[placement.publication_format as keyof typeof PUBLICATION_FORMATS]
    const durationText = formatInfo ? formatDurationHours(formatInfo.multiplier * 24) : ''
    const schedule = placement.final_schedule ?? placement.proposed_schedule
    events.push({
      id: 'waiting_placement',
      icon: '⏳',
      title: 'Ожидает публикации',
      subtitle: schedule
        ? `Запланировано: ${formatDateTimeMSK(schedule)} (${durationText})`
        : `Ожидает публикации владельцем (${durationText})`,
      variant: 'warning',
    })
  }

  // Stage 6: Published
  if (isPublished || isCompleted) {
    const deletionInfo = calcDeletionRemaining(
      placement.scheduled_delete_at,
      placement.published_at,
      placement.publication_format,
    )

    events.push({
      id: 'published',
      icon: '✅',
      title: 'Опубликовано',
      subtitle: placement.published_at ? formatDateTimeMSK(placement.published_at) : 'Опубликовано',
      variant: 'success',
    })

    // Stage 7: Deletion countdown (only if not yet deleted and not completed)
    if (isPublished && deletionInfo) {
      events.push({
        id: 'deletion_countdown',
        icon: '⏳',
        title: 'Удаление через',
        subtitle: deletionInfo.remainingText,
        variant: 'warning',
      })
    }
  }

  // Stage 8: Completed (escrow released after deletion)
  if (isCompleted) {
    const deletedSubtitle = placement.deleted_at ? formatDateTimeMSK(placement.deleted_at) : 'Пост удалён'
    events.push({
      id: 'deleted',
      icon: '✅',
      title: 'Пост удалён',
      subtitle: deletedSubtitle,
      variant: 'success',
    })
    events.push({
      id: 'completed',
      icon: '🎉',
      title: 'Кампания завершена',
      subtitle: 'Эскроу освобождён, средства перечислены владельцу',
      variant: 'success',
    })
  }

  // ERID status (always shown if erid field exists)
  if (placement.erid !== undefined) {
    events.push({
      id: 'erid',
      icon: placement.erid ? '✅' : '⏳',
      title: placement.erid ? 'ERID присвоен' : 'ERID ожидается',
      subtitle: placement.erid ? placement.erid : 'Маркировка в процессе',
      variant: placement.erid ? 'success' : 'default',
    })
  }

  return events
}

export default function CampaignWaiting() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const haptic = useHaptic()

  const numId = id ? parseInt(id, 10) : null
  const { data: placement, isLoading } = usePlacement(numId, { refetchInterval: 10_000 })
  const { mutate: updatePlacement, isPending: cancelling } = useUpdatePlacement()

  const isExpired = placement?.expires_at ? new Date(placement.expires_at) < new Date() : false
  const isTerminal = placement ? ['cancelled', 'failed', 'refunded', 'failed_permissions', 'completed'].includes(placement.status) : false

  // Redirect only for active status transitions (payment, published)
  // Terminal states should stay on this screen to show details
  useEffect(() => {
    if (!placement) return
    const path = getRedirectPath(placement.id, placement.status)
    if (path) navigate(path)
  }, [placement?.status]) // eslint-disable-line react-hooks/exhaustive-deps

  if (isLoading) {
    return (
      <ScreenShell>
        <Skeleton height={60} />
        <Skeleton height={200} />
        <Skeleton height={120} />
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

  const formatInfo = PUBLICATION_FORMATS[placement.publication_format]
  const timelineEvents = buildTimelineEvents(placement, isExpired, isTerminal)
  const isPaid = placement.status === 'escrow' || placement.status === 'published'
  const isCompleted = placement.status === 'completed'
  const isWaitingPlacement = placement.status === 'escrow' && !isPaid

  const handleCancel = () => {
    haptic.warning()
    updatePlacement(
      { id: placement.id, data: { action: 'cancel' } },
      { onSuccess: () => { navigate('/adv/campaigns') } },
    )
  }

  return (
    <ScreenShell>
      {isCompleted ? (
        <Notification type="success">
          🎉 Кампания #{placement.id} завершена. Пост удалён, средства перечислены владельцу.
          {placement.erid && <div className="mt-1 text-sm opacity-80">ERID: {placement.erid}</div>}
        </Notification>
      ) : isTerminal ? (
        <Notification type="danger">
          {placement.status === 'cancelled' && '❌ Кампания отменена'}
          {placement.status === 'failed' && '⚠️ Ошибка публикации'}
          {placement.status === 'failed_permissions' && '⚠️ Нет прав у бота для публикации'}
          {placement.status === 'refunded' && '💸 Средства возвращены на баланс'}
          {placement.rejection_reason && <div className="mt-1 text-sm opacity-80">{placement.rejection_reason}</div>}
        </Notification>
      ) : isExpired && placement.status === 'pending_owner' ? (
        <Notification type="danger">
          ⏰ Срок ответа владельца истёк. Заявка #{placement.id} будет автоматически отменена.
        </Notification>
      ) : isWaitingPlacement ? (
        <Notification type="info">
          ⏳ Оплата подтверждена — ожидаем публикации заявки #{placement.id} владельцем канала
        </Notification>
      ) : (
        <Notification type={isPaid ? 'success' : 'info'}>
          {isPaid
            ? `✅ Оплата получена — ожидаем публикации заявки #${placement.id}`
            : `⏳ Заявка #${placement.id} отправлена владельцу канала`}
        </Notification>
      )}

      <Card title="Статус заявки" className={styles.card}>
        <Timeline events={timelineEvents} />
      </Card>

      <ArbitrationPanel title={`Детали заявки #${placement.id}`}>
        <div className={styles.rows}>
          <div className={styles.row}>
            <span className={styles.label}>📺 Канал</span>
            <span className={styles.value}>@{placement.channel?.username ?? `#${placement.channel_id}`}</span>
          </div>
          <div className={styles.row}>
            <span className={styles.label}>📄 Формат</span>
            <span className={styles.value}>{formatInfo.name}</span>
          </div>
          <div className={styles.row}>
            <span className={styles.label}>💰 Цена</span>
            <span className={styles.value}>{formatCurrency(placement.final_price ?? placement.counter_price ?? placement.proposed_price)}</span>
          </div>
          <div className={styles.row}>
            <span className={styles.label}>📅 Дата</span>
            <span className={styles.value}>{formatDateTimeMSK(placement.final_schedule ?? placement.proposed_schedule)}</span>
          </div>
        </div>
      </ArbitrationPanel>

      <Button variant="secondary" fullWidth onClick={() => navigate('/adv')}>
        ← В меню рекламодателя
      </Button>

      {!isTerminal && (
        <Button
          variant="danger"
          fullWidth
          disabled={cancelling}
          onClick={handleCancel}
        >
          {cancelling ? '⏳ Отмена...' : '❌ Отменить заявку'}
        </Button>
      )}
    </ScreenShell>
  )
}
