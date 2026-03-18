import { useParams, useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Notification, Card, Button, Skeleton } from '@/components/ui'
import { formatCurrency, formatTime, formatDateTime } from '@/lib/formatters'
import { useHaptic } from '@/hooks/useHaptic'
import { usePlacement } from '@/hooks/queries'
import styles from './CampaignPublished.module.css'

const PLATFORM_COMMISSION = 0.15

export default function CampaignPublished() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const haptic = useHaptic()

  const numId = id ? parseInt(id, 10) : null
  const { data: placement, isLoading } = usePlacement(numId)

  if (isLoading) {
    return (
      <ScreenShell>
        <Skeleton height={60} />
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

  const price = parseFloat(placement.final_price ?? placement.proposed_price)
  const ownerShare = price * (1 - PLATFORM_COMMISSION)
  const platformShare = price * PLATFORM_COMMISSION

  const isWithinDisputeWindow = (() => {
    if (!placement.published_at) return false
    const diffH = (Date.now() - new Date(placement.published_at).getTime()) / 3_600_000
    return diffH < 48
  })()

  const canDispute = isWithinDisputeWindow && !placement.has_dispute

  return (
    <ScreenShell>
      <Notification type="success">
        <span style={{ fontWeight: 600 }}>🎉 Публикация успешна!</span>
      </Notification>

      <Card title="Результат" className={styles.card}>
        <div className={styles.rows}>
          <div className={styles.row}>
            <span className={styles.label}>@{placement.channel?.username ?? `#${placement.channel_id}`}</span>
            <span className={styles.valueSuccess}>
              ✅ {placement.published_at ? formatTime(placement.published_at) : '—'}
            </span>
          </div>

          <div className={styles.divider} />

          <div className={styles.row}>
            <span className={styles.label}>Владельцу (85%)</span>
            <span className={styles.value}>{formatCurrency(ownerShare)}</span>
          </div>
          <div className={styles.row}>
            <span className={styles.labelMuted}>Комиссия платформы (15%)</span>
            <span className={styles.valueMuted}>{formatCurrency(platformShare)}</span>
          </div>

          <div className={styles.divider} />

          <div className={styles.row}>
            <span className={styles.label}>Удаление поста</span>
            <span className={styles.value}>
              {placement.scheduled_delete_at ? formatDateTime(placement.scheduled_delete_at) : '—'} 🤖
            </span>
          </div>
        </div>
      </Card>

      <div className={styles.buttons}>
        <Button
          variant="primary"
          fullWidth
          onClick={() => {
            haptic.success()
            alert('Отзыв — Phase 12')
          }}
        >
          ⭐ Оставить отзыв
        </Button>

        <Button variant="secondary" fullWidth onClick={() => navigate('/adv/analytics')}>
          📊 В статистику
        </Button>

        {canDispute && (
          <Button
            variant="danger"
            fullWidth
            onClick={() => navigate(`/adv/campaigns/${placement.id}/dispute`)}
          >
            ⚠️ Пожаловаться
          </Button>
        )}
      </div>
    </ScreenShell>
  )
}
