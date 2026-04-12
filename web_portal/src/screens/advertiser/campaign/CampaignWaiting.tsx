import { useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Notification, Card, Timeline, ArbitrationPanel, Button, Skeleton } from '@shared/ui'
import { PUBLICATION_FORMATS, formatCurrency, formatDateTimeMSK } from '@/lib/constants'
import { usePlacement, useUpdatePlacement } from '@/hooks/useCampaignQueries'

function formatDateTime(dt: string | null | undefined): string {
  return formatDateTimeMSK(dt)
}

/** Redirect only for transitions to fundamentally different screens (payment, published). */
function getRedirectPath(id: number, status: string): string | null {
  if (status === 'pending_payment' || status === 'counter_offer') return `/adv/campaigns/${id}/payment`
  if (status === 'published') return `/adv/campaigns/${id}/published`
  // Terminal states (cancelled/failed/refunded) should stay here — this screen shows their details
  return null
}

export default function CampaignWaiting() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const numId = id ? parseInt(id, 10) : null
  const { data: placement, isLoading } = usePlacement(numId, { refetchInterval: 10_000 })
  const { mutate: updatePlacement, isPending: cancelling } = useUpdatePlacement()

  const isExpired = placement?.expires_at ? new Date(placement.expires_at) < new Date() : false
  const isTerminal = placement ? ['cancelled', 'failed', 'refunded', 'failed_permissions'].includes(placement.status) : false

  // Redirect only for active status transitions (payment, published)
  // Terminal states should stay on this screen to show details
  useEffect(() => {
    if (!placement) return
    const path = getRedirectPath(numId ?? 0, placement.status)
    if (path) navigate(path, { replace: true })
  }, [placement?.status, navigate, numId, placement])

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

  // At this point, placement is guaranteed to be defined
  const p = placement

  const formatInfo = PUBLICATION_FORMATS[p.publication_format]
  const isPaid = p.status === 'escrow' || p.status === 'published'

  function getWaitingIcon(): string {
    if (p.status === 'cancelled') return '🚫'
    if (p.status === 'failed' || p.status === 'failed_permissions') return '⚠️'
    if (p.status === 'refunded') return '💸'
    if (isPaid) return '✅'
    if (isExpired) return '⏰'
    return '⏳'
  }
  function getWaitingTitle(): string {
    if (p.status === 'cancelled') return 'Отменено'
    if (p.status === 'failed' || p.status === 'failed_permissions') return 'Ошибка публикации'
    if (p.status === 'refunded') return 'Возврат средств'
    if (isPaid) return 'Владелец принял'
    if (isExpired) return 'Срок ответа истёк'
    return 'Ожидает ответа владельца'
  }
  function getWaitingSubtitle(): string {
    if (p.status === 'cancelled' && p.rejection_reason) return p.rejection_reason
    if (p.status === 'failed' && p.rejection_reason) return p.rejection_reason
    if (p.status === 'refunded') return 'Средства возвращены на баланс'
    if (isPaid) return ''
    if (!isExpired) return `До ${formatDateTime(p.expires_at)} (24 ч)`
    return ''
  }
  function getWaitingVariant(): 'success' | 'default' | 'warning' | 'danger' {
    if (p.status === 'cancelled') return 'danger'
    if (p.status === 'failed' || p.status === 'failed_permissions') return 'danger'
    if (p.status === 'refunded') return 'warning'
    if (isPaid) return 'success'
    if (isExpired) return 'default'
    return 'warning'
  }

  const timelineEvents = [
    {
      id: 'created',
      icon: '✅',
      title: 'Заявка создана',
      subtitle: formatDateTime(p.created_at),
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
      icon: p.status === 'published' ? '✅' : '📢',
      title: 'Публикация',
      subtitle: p.status === 'published'
        ? formatDateTime(p.published_at)
        : formatDateTime(p.final_schedule ?? p.proposed_schedule) || 'Запланировано',
      variant: p.status === 'published' ? 'success' as const : 'default' as const,
    },
  ]

  const handleCancel = () => {
    updatePlacement(
      { id: p.id, data: { action: 'cancel' } },
      { onSuccess: () => navigate('/adv/campaigns') },
    )
  }

  return (
    <div className="space-y-6">
      {isTerminal ? (
        <Notification type="danger">
          {p.status === 'cancelled' && '❌ Кампания отменена'}
          {p.status === 'failed' && '⚠️ Ошибка публикации'}
          {p.status === 'failed_permissions' && '⚠️ Нет прав у бота для публикации'}
          {p.status === 'refunded' && '💸 Средства возвращены на баланс'}
          {p.rejection_reason && <span className="block mt-1 text-sm opacity-80">{p.rejection_reason}</span>}
        </Notification>
      ) : isExpired && p.status === 'pending_owner' ? (
        <Notification type="danger">
          ⏰ Срок ответа владельца истёк. Заявка #{p.id} будет автоматически отменена.
        </Notification>
      ) : (
        <Notification type={isPaid ? 'success' : 'info'}>
          {isPaid
            ? `✅ Оплата получена — ожидаем публикации заявки #${p.id}`
            : `⏳ Заявка #${p.id} отправлена владельцу канала`}
        </Notification>
      )}

      <Card title="Статус заявки">
        <Timeline events={timelineEvents} />
      </Card>

      <ArbitrationPanel title={`Детали заявки #${p.id}`}>
        <div className="space-y-2 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-text-secondary">📺 Канал</span>
            <span className="text-text-primary font-medium">
              @{p.channel?.username ?? `#${p.channel_id}`}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-text-secondary">📄 Формат</span>
            <span className="text-text-primary">{formatInfo?.name ?? p.publication_format}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-text-secondary">💰 Цена</span>
            <span className="text-text-primary font-semibold">{formatCurrency(p.final_price ?? p.counter_price ?? p.proposed_price)}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-text-secondary">📅 Дата</span>
            <span className="text-text-primary">{formatDateTime(p.final_schedule ?? p.proposed_schedule)}</span>
          </div>
        </div>
      </ArbitrationPanel>

      <div className="flex flex-col gap-3">
        <Button variant="secondary" fullWidth onClick={() => navigate('/adv/campaigns')}>
          ← Мои кампании
        </Button>
        {!isTerminal && (
          <Button variant="danger" fullWidth loading={cancelling} onClick={handleCancel}>
            {cancelling ? '⏳ Отмена...' : '❌ Отменить заявку'}
          </Button>
        )}
      </div>
    </div>
  )
}
