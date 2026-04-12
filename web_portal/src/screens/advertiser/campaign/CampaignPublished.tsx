import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Notification, Card, Button, Skeleton, StatusPill } from '@shared/ui'
import { formatCurrency, formatDateTimeMSK, formatTimeMSK } from '@/lib/constants'
import { usePlacement } from '@/hooks/useCampaignQueries'

const PLATFORM_COMMISSION = 0.15

function formatDateTime(dt: string | null | undefined): string {
  return formatDateTimeMSK(dt)
}

function formatTime(dt: string | null | undefined): string {
  return formatTimeMSK(dt)
}

export default function CampaignPublished() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const numId = id ? parseInt(id, 10) : null
  const { data: placement, isLoading } = usePlacement(numId)

  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const interval = setInterval(() => setNow(Date.now()), 60000)
    return () => clearInterval(interval)
  }, [])

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-20" />
        <Skeleton className="h-40" />
      </div>
    )
  }

  if (!placement) {
    return <Notification type="danger">Заявка не найдена</Notification>
  }

  const price = parseFloat(String(placement.final_price ?? placement.counter_price ?? placement.proposed_price))
  const ownerShare = price * (1 - PLATFORM_COMMISSION)
  const platformShare = price * PLATFORM_COMMISSION

  const isWithinDisputeWindow = placement.published_at
    ? (now - new Date(placement.published_at).getTime()) / 3_600_000 < 48
    : false

  const canDispute = isWithinDisputeWindow && !placement.has_dispute

  return (
    <div className="space-y-6">
      <Notification type="success">
        <span className="font-semibold">🎉 Публикация успешна!</span>
      </Notification>

      <Card title="Результат">
        <div className="space-y-3 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-text-secondary">
              @{placement.channel?.username ?? `#${placement.channel_id}`}
            </span>
            <span className="text-success font-semibold">
              ✅ {placement.published_at ? formatTime(placement.published_at) : '—'}
            </span>
          </div>

          <div className="border-t border-border pt-3">
            <div className="flex items-center justify-between">
              <span className="text-text-secondary">Владельцу (85%)</span>
              <span className="text-text-primary font-medium">{formatCurrency(ownerShare)}</span>
            </div>
            <div className="flex items-center justify-between mt-1">
              <span className="text-text-tertiary">Комиссия платформы (15%)</span>
              <span className="text-text-tertiary">{formatCurrency(platformShare)}</span>
            </div>
          </div>

          <div className="border-t border-border pt-3">
            <div className="flex items-center justify-between">
              <span className="text-text-secondary">Удаление поста</span>
              <span className="text-text-primary">
                {placement.scheduled_delete_at ? formatDateTime(placement.scheduled_delete_at) : '—'} 🤖
              </span>
            </div>
          </div>
        </div>
      </Card>

      {placement.erid !== undefined && (
        <Card>
          <StatusPill status={placement.erid ? 'success' : 'warning'}>
            {placement.erid ? `erid: ${placement.erid}` : 'erid: ожидается'}
          </StatusPill>
          {placement.erid && (
            <p className="text-xs text-text-tertiary mt-2 font-mono break-all">
              Токен маркировки: {placement.erid}
            </p>
          )}
        </Card>
      )}

      <div className="flex flex-col gap-3">
        <Button variant="secondary" fullWidth onClick={() => navigate(`/campaign/${placement.id}/ord`)}>
          Статус ORD →
        </Button>
        <Button variant="primary" fullWidth onClick={() => navigate('/adv/campaigns')}>
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
    </div>
  )
}
