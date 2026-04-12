import React from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Notification, Card, Button, Skeleton, StatusPill, Text } from '@/components/ui'
import { formatCurrency, formatTime, formatDateTime } from '@/lib/formatters'
import { usePlacement } from '@/hooks/queries'
import styles from './CampaignPublished.module.css'

const PLATFORM_COMMISSION = 0.15

export default function CampaignPublished() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const numId = id ? parseInt(id, 10) : null
  const { data: placement, isLoading } = usePlacement(numId)

  // Hooks must be called unconditionally at the top level
  const [now, setNow] = React.useState(() => Date.now())

  React.useEffect(() => {
    const interval = setInterval(() => setNow(Date.now()), 60000) // Update every minute
    return () => clearInterval(interval)
  }, [])

  const isWithinDisputeWindow = placement?.published_at
    ? (now - new Date(placement.published_at).getTime()) / 3_600_000 < 48
    : false

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

  const price = parseFloat(placement.final_price ?? placement.counter_price ?? placement.proposed_price)
  const ownerShare = price * (1 - PLATFORM_COMMISSION)
  const platformShare = price * PLATFORM_COMMISSION

  const canDispute = isWithinDisputeWindow && !placement.has_dispute

  return (
    <ScreenShell>
      <Notification type="success">
        <Text weight="semibold">🎉 Публикация успешна!</Text>
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

      {placement.erid !== undefined && (
        <div className={styles.eridSection}>
          <StatusPill status={placement.erid ? 'success' : 'warning'} size="sm">
            {placement.erid ? `erid: ${placement.erid}` : 'erid: ожидается'}
          </StatusPill>
          {placement.erid && (
            <Text variant="xs" color="muted" font="mono" className={styles.eridToken}>
              Токен маркировки: {placement.erid}
            </Text>
          )}
        </div>
      )}

      <div className={styles.ordButtonSection}>
        <Button variant="secondary" fullWidth onClick={() => navigate(`/adv/campaigns/${placement.id}/ord`)}>
          Статус ORD →
        </Button>
      </div>

      <div className={styles.buttons}>
        <Button variant="primary" fullWidth onClick={() => navigate('/adv')}>
          ← В меню рекламодателя
        </Button>

        <Button variant="secondary" fullWidth onClick={() => navigate('/adv/campaigns')}>
          📋 Мои кампании
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
