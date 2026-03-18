import { useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Notification, Card, Timeline, ArbitrationPanel, Button, Skeleton } from '@/components/ui'
import { PUBLICATION_FORMATS } from '@/lib/constants'
import { formatDateTime, formatCurrency } from '@/lib/formatters'
import { useHaptic } from '@/hooks/useHaptic'
import { usePlacement, useUpdatePlacement } from '@/hooks/queries'
import styles from './CampaignWaiting.module.css'

export default function CampaignWaiting() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const haptic = useHaptic()

  const numId = id ? parseInt(id, 10) : null
  const { data: placement, isLoading } = usePlacement(numId)
  const { mutate: updatePlacement, isPending: cancelling } = useUpdatePlacement()

  // Poll for status changes and redirect
  useEffect(() => {
    if (!placement) return
    if (placement.status === 'pending_payment' || placement.status === 'counter_offer') {
      navigate(`/adv/campaigns/${placement.id}/payment`)
    } else if (placement.status === 'published') {
      navigate(`/adv/campaigns/${placement.id}/published`)
    }
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

  const timelineEvents = [
    {
      id: 'created',
      icon: '✅',
      title: 'Заявка создана',
      subtitle: formatDateTime(placement.created_at),
      variant: 'success' as const,
    },
    {
      id: 'waiting',
      icon: '⏳',
      title: 'Ожидает ответа владельца',
      subtitle: `До ${formatDateTime(placement.expires_at)} (24 ч)`,
      variant: 'warning' as const,
    },
    {
      id: 'payment',
      icon: '💳',
      title: 'Оплата',
      subtitle: 'После подтверждения',
      variant: 'default' as const,
    },
    {
      id: 'escrow',
      icon: '🔒',
      title: 'Эскроу',
      subtitle: '',
      variant: 'default' as const,
    },
    {
      id: 'published',
      icon: '📢',
      title: 'Публикация',
      subtitle: '',
      variant: 'default' as const,
    },
  ]

  return (
    <ScreenShell>
      <Notification type="info">
        ⏳ Заявка #{placement.id} отправлена владельцу канала
      </Notification>

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

      <Button
        variant="danger"
        fullWidth
        disabled={cancelling}
        onClick={() => {
          haptic.warning()
          updatePlacement(
            { id: placement.id, data: { action: 'cancel' } },
            { onSuccess: () => navigate('/adv/campaigns') },
          )
        }}
      >
        {cancelling ? '⏳ Отмена...' : '❌ Отменить заявку'}
      </Button>
    </ScreenShell>
  )
}
