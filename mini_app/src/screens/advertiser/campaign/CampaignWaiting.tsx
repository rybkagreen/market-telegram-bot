import { useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Notification, Card, Timeline, ArbitrationPanel, Button, Skeleton } from '@/components/ui'
import { PUBLICATION_FORMATS } from '@/lib/constants'
import { formatDateTime, formatCurrency } from '@/lib/formatters'
import { useHaptic } from '@/hooks/useHaptic'
import { usePlacement, useUpdatePlacement } from '@/hooks/queries'
import styles from './CampaignWaiting.module.css'

type Variant = 'success' | 'warning' | 'default'
type TimelineEvent = { id: string; icon: string; title: string; subtitle: string; variant: Variant }

function getRedirectPath(id: number, status: string): string | null {
  if (status === 'pending_payment' || status === 'counter_offer') return `/adv/campaigns/${id}/payment`
  if (status === 'published') return `/adv/campaigns/${id}/published`
  if (status === 'cancelled' || status === 'failed' || status === 'refunded') return '/adv/campaigns'
  return null
}

function publishedSubtitle(publishedAt: string | null | undefined, proposedSchedule: string | null | undefined, isPublished: boolean): string {
  if (isPublished) return formatDateTime(publishedAt ?? '')
  if (proposedSchedule) return `Запланировано: ${formatDateTime(proposedSchedule)}`
  return ''
}

function buildTimelineEvents(placement: { status: string; created_at: string; expires_at: string; published_at?: string | null; proposed_schedule?: string | null }, isExpired: boolean): TimelineEvent[] {
  const st = placement.status
  const isPastOwner = ['pending_payment', 'counter_offer', 'escrow', 'published'].includes(st)
  const isPastPayment = ['escrow', 'published'].includes(st)
  const isPublished = st === 'published'
  const ownerWaiting = !isPastOwner && !isExpired
  return [
    { id: 'created', icon: '✅', title: 'Заявка создана', subtitle: formatDateTime(placement.created_at), variant: 'success' },
    { id: 'waiting', icon: isPastOwner ? '✅' : isExpired ? '⏰' : '⏳', title: isPastOwner ? 'Владелец принял' : isExpired ? 'Срок ответа истёк' : 'Ожидает ответа владельца', subtitle: isPastOwner ? '' : ownerWaiting ? `До ${formatDateTime(placement.expires_at)} (24 ч)` : '', variant: isPastOwner ? 'success' : isExpired ? 'default' : 'warning' },
    { id: 'payment', icon: isPastPayment ? '✅' : '💳', title: isPastPayment ? 'Оплачено' : 'Оплата', subtitle: isPastPayment ? '' : 'После подтверждения', variant: isPastPayment ? 'success' : 'default' },
    { id: 'escrow', icon: isPastPayment ? '✅' : '🔒', title: 'Эскроу', subtitle: isPastPayment ? 'Средства заблокированы' : '', variant: isPastPayment ? 'success' : 'default' },
    { id: 'published', icon: isPublished ? '✅' : '📢', title: 'Публикация', subtitle: publishedSubtitle(placement.published_at, placement.proposed_schedule, isPublished), variant: isPublished ? 'success' : 'default' },
  ]
}

export default function CampaignWaiting() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const haptic = useHaptic()

  const numId = id ? parseInt(id, 10) : null
  const { data: placement, isLoading } = usePlacement(numId, { refetchInterval: 10_000 })
  const { mutate: updatePlacement, isPending: cancelling } = useUpdatePlacement()

  const isExpired = placement?.expires_at ? new Date(placement.expires_at) < new Date() : false

  // Poll for status changes and redirect
  useEffect(() => {
    if (!placement) return
    const path = getRedirectPath(placement.id, placement.status)
    if (path) navigate(path)
    // Redirect expired placements in pending_owner state back to campaigns list
    if (isExpired && placement.status === 'pending_owner') {
      navigate('/adv/campaigns', { replace: true })
    }
  }, [placement?.status, isExpired]) // eslint-disable-line react-hooks/exhaustive-deps

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
  const timelineEvents = buildTimelineEvents(placement, isExpired)

  const handleCancel = () => {
    haptic.warning()
    updatePlacement(
      { id: placement.id, data: { action: 'cancel' } },
      { onSuccess: () => { navigate('/adv/campaigns') } },
    )
  }

  const isPaid = placement.status === 'escrow' || placement.status === 'published'

  return (
    <ScreenShell>
      {isExpired && placement.status === 'pending_owner' ? (
        <Notification type="danger">
          ⏰ Срок ответа владельца истёк. Заявка #{placement.id} будет автоматически отменена.
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
            <span className={styles.value}>{formatCurrency(placement.proposed_price)}</span>
          </div>
          <div className={styles.row}>
            <span className={styles.label}>📅 Дата</span>
            <span className={styles.value}>{formatDateTime(placement.proposed_schedule)}</span>
          </div>
        </div>
      </ArbitrationPanel>

      <Button variant="secondary" fullWidth onClick={() => navigate('/adv')}>
        ← В меню рекламодателя
      </Button>

      <Button
        variant="danger"
        fullWidth
        disabled={cancelling}
        onClick={handleCancel}
      >
        {cancelling ? '⏳ Отмена...' : '❌ Отменить заявку'}
      </Button>
    </ScreenShell>
  )
}
