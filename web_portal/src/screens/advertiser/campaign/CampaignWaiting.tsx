import { useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Notification, Card, Timeline, ArbitrationPanel, Button, Skeleton } from '@shared/ui'
import { PUBLICATION_FORMATS } from '@/lib/constants'
import { formatCurrency } from '@/lib/constants'
import { usePlacement, useUpdatePlacement } from '@/hooks/useCampaignQueries'

function formatDateTime(dt: string | null | undefined): string {
  if (!dt) return '—'
  return new Date(dt).toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function getRedirectPath(id: number, status: string): string | null {
  if (status === 'pending_payment' || status === 'counter_offer') return `/adv/campaigns/${id}/payment`
  if (status === 'published') return `/adv/campaigns/${id}/published`
  if (status === 'cancelled' || status === 'failed' || status === 'refunded') return '/adv/campaigns'
  return null
}

export default function CampaignWaiting() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const numId = id ? parseInt(id, 10) : null
  const { data: placement, isLoading } = usePlacement(numId, { refetchInterval: 10_000 })
  const { mutate: updatePlacement, isPending: cancelling } = useUpdatePlacement()

  const isExpired = placement?.expires_at ? new Date(placement.expires_at) < new Date() : false

  // Poll for status changes and redirect
  useEffect(() => {
    if (!placement) return
    const path = getRedirectPath(numId ?? 0, placement.status)
    if (path) navigate(path, { replace: true })
    if (isExpired && placement.status === 'pending_owner') {
      navigate('/adv/campaigns', { replace: true })
    }
  }, [placement?.status, isExpired, navigate, numId])

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-20" />
        <Skeleton className="h-40" />
        <Skeleton className="h-20" />
      </div>
    )
  }

  if (!placement) {
    return <Notification type="danger">Заявка не найдена</Notification>
  }

  const formatInfo = PUBLICATION_FORMATS[placement.publication_format]
  const isPaid = placement.status === 'escrow' || placement.status === 'published'

  function getWaitingIcon(): string {
    if (isPaid) return '✅'
    if (isExpired) return '⏰'
    return '⏳'
  }
  function getWaitingTitle(): string {
    if (isPaid) return 'Владелец принял'
    if (isExpired) return 'Срок ответа истёк'
    return 'Ожидает ответа владельца'
  }
  function getWaitingSubtitle(): string {
    if (isPaid) return ''
    if (!isExpired) return `До ${formatDateTime(placement?.expires_at)} (24 ч)`
    return ''
  }
  function getWaitingVariant(): 'success' | 'default' | 'warning' {
    if (isPaid) return 'success'
    if (isExpired) return 'default'
    return 'warning'
  }

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
      icon: getWaitingIcon(),
      title: getWaitingTitle(),
      subtitle: getWaitingSubtitle(),
      variant: getWaitingVariant(),
    },
    {
      id: 'payment',
      icon: isPaid ? '✅' : '💳',
      title: isPaid ? 'Оплачено' : 'Оплата',
      subtitle: isPaid ? 'Средства в эскроу' : 'После подтверждения',
      variant: isPaid ? 'success' as const : 'default' as const,
    },
    {
      id: 'published',
      icon: placement.status === 'published' ? '✅' : '📢',
      title: 'Публикация',
      subtitle: placement.status === 'published' ? formatDateTime(placement.published_at) : 'Запланировано',
      variant: placement.status === 'published' ? 'success' as const : 'default' as const,
    },
  ]

  const handleCancel = () => {
    updatePlacement(
      { id: placement.id, data: { action: 'cancel' } },
      { onSuccess: () => navigate('/adv/campaigns') },
    )
  }

  return (
    <div className="space-y-6">
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

      <Card title="Статус заявки">
        <Timeline events={timelineEvents} />
      </Card>

      <ArbitrationPanel title={`Детали заявки #${placement.id}`}>
        <div className="space-y-2 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-text-secondary">📺 Канал</span>
            <span className="text-text-primary font-medium">
              @{placement.channel?.username ?? `#${placement.channel_id}`}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-text-secondary">📄 Формат</span>
            <span className="text-text-primary">{formatInfo?.name ?? placement.publication_format}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-text-secondary">💰 Цена</span>
            <span className="text-text-primary font-semibold">{formatCurrency(placement.proposed_price)}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-text-secondary">📅 Дата</span>
            <span className="text-text-primary">{formatDateTime(placement.proposed_schedule)}</span>
          </div>
        </div>
      </ArbitrationPanel>

      <div className="flex flex-col gap-3">
        <Button variant="secondary" fullWidth onClick={() => navigate('/adv/campaigns')}>
          ← Мои кампании
        </Button>
        <Button variant="danger" fullWidth loading={cancelling} onClick={handleCancel}>
          {cancelling ? '⏳ Отмена...' : '❌ Отменить заявку'}
        </Button>
      </div>
    </div>
  )
}
