import React from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Notification, Card, Button, Skeleton, StatusPill, Text } from '@/components/ui'
import { formatCurrency, formatTime, formatDateTime } from '@/lib/formatters'
import {
  OWNER_NET_RATE,
  PLATFORM_COMMISSION_GROSS,
  PLATFORM_TOTAL_RATE,
  SERVICE_FEE,
  computePlacementSplit,
  formatRatePct,
} from '@/lib/constants'
import { usePlacement } from '@/hooks/queries'
import styles from './CampaignPublished.module.css'

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
  // Промт 15.7: derive split from shared constants (no hardcoded effective rates).
  const split = computePlacementSplit(price)
  const ownerShare = split.ownerNet
  const platformShare = split.platformTotal

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
            <span className={styles.label}>{`Владельцу (${formatRatePct(OWNER_NET_RATE)})`}</span>
            <span className={styles.value}>{formatCurrency(ownerShare)}</span>
          </div>
          <div className={styles.row}>
            <span className={styles.labelMuted}>{`Платформа (${formatRatePct(PLATFORM_TOTAL_RATE)} — ${formatRatePct(PLATFORM_COMMISSION_GROSS, 0)} + ${formatRatePct(SERVICE_FEE)} сервисный сбор)`}</span>
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

        <Button variant="secondary" fullWidth onClick={() => navigate('/analytics?role=advertiser')}>
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
