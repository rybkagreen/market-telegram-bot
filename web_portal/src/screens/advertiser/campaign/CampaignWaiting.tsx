import { useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Notification, Timeline, Button, Skeleton, Icon, ScreenHeader } from '@shared/ui'
import { PUBLICATION_FORMATS, formatCurrency, formatDateTimeMSK } from '@/lib/constants'
import { usePlacement, useUpdatePlacement } from '@/hooks/useCampaignQueries'

function getRedirectPath(id: number, status: string): string | null {
  if (status === 'pending_payment' || status === 'counter_offer') return `/adv/campaigns/${id}/payment`
  if (status === 'published') return `/adv/campaigns/${id}/published`
  return null
}

export default function CampaignWaiting() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const numId = id ? parseInt(id, 10) : null
  const { data: placement, isLoading } = usePlacement(numId, { refetchInterval: 10_000 })
  const { mutate: updatePlacement, isPending: cancelling } = useUpdatePlacement()

  const isExpired = placement?.expires_at ? new Date(placement.expires_at) < new Date() : false
  const isTerminal = placement
    ? ['cancelled', 'failed', 'refunded', 'failed_permissions'].includes(placement.status)
    : false

  useEffect(() => {
    if (!placement) return
    const path = getRedirectPath(numId ?? 0, placement.status)
    if (path) navigate(path, { replace: true })
  }, [placement?.status, navigate, numId, placement])

  if (isLoading) {
    return (
      <div className="max-w-[900px] mx-auto space-y-4">
        <Skeleton className="h-20" />
        <Skeleton className="h-56" />
        <Skeleton className="h-28" />
      </div>
    )
  }

  if (!placement) {
    return (
      <div className="max-w-[900px] mx-auto">
        <Notification type="danger">Заявка не найдена</Notification>
      </div>
    )
  }

  const p = placement
  const formatInfo = PUBLICATION_FORMATS[p.publication_format]
  const isPaid = p.status === 'escrow' || p.status === 'published'

  const waitingTitle = (() => {
    if (p.status === 'cancelled') return 'Отменено'
    if (p.status === 'failed' || p.status === 'failed_permissions') return 'Ошибка публикации'
    if (p.status === 'refunded') return 'Возврат средств'
    if (isPaid) return 'Владелец принял'
    if (isExpired) return 'Срок ответа истёк'
    return 'Ожидает ответа владельца'
  })()

  const waitingSubtitle = (() => {
    if (p.status === 'cancelled' && p.rejection_reason) return p.rejection_reason
    if (p.status === 'failed' && p.rejection_reason) return p.rejection_reason
    if (p.status === 'refunded') return 'Средства возвращены на баланс'
    if (isPaid) return ''
    if (!isExpired) return `До ${formatDateTimeMSK(p.expires_at)} (24 ч)`
    return ''
  })()

  const waitingVariant: 'success' | 'default' | 'warning' | 'danger' = (() => {
    if (p.status === 'cancelled') return 'danger'
    if (p.status === 'failed' || p.status === 'failed_permissions') return 'danger'
    if (p.status === 'refunded') return 'warning'
    if (isPaid) return 'success'
    if (isExpired) return 'default'
    return 'warning'
  })()

  const timelineEvents = [
    {
      id: 'created',
      icon: '',
      title: 'Заявка создана',
      subtitle: formatDateTimeMSK(p.created_at),
      variant: 'success' as const,
    },
    {
      id: 'waiting',
      icon: '',
      title: waitingTitle,
      subtitle: waitingSubtitle,
      variant: waitingVariant,
    },
    {
      id: 'payment',
      icon: '',
      title: isPaid ? 'Оплачено' : 'Оплата',
      subtitle: isPaid ? 'Средства в эскроу' : 'После подтверждения владельца',
      variant: isPaid ? ('success' as const) : ('default' as const),
    },
    {
      id: 'published',
      icon: '',
      title: 'Публикация',
      subtitle:
        p.status === 'published'
          ? formatDateTimeMSK(p.published_at)
          : formatDateTimeMSK(p.final_schedule ?? p.proposed_schedule) || 'Запланировано',
      variant: p.status === 'published' ? ('success' as const) : ('default' as const),
    },
  ]

  const handleCancel = () => {
    updatePlacement(
      { id: p.id, data: { action: 'cancel' } },
      { onSuccess: () => navigate('/adv/campaigns') },
    )
  }

  return (
    <div className="max-w-[900px] mx-auto">
      <ScreenHeader
        crumbs={['Главная', 'Рекламодатель', 'Кампании', `#${p.id}`]}
        title={`Заявка #${p.id}`}
        subtitle={`@${p.channel?.username ?? `#${p.channel_id}`} · ${formatInfo?.name ?? p.publication_format}`}
        action={
          <Button
            variant="secondary"
            iconLeft="arrow-left"
            onClick={() => navigate('/adv/campaigns')}
          >
            К списку
          </Button>
        }
      />

      <div className="mb-5">
        {isTerminal ? (
          <Notification type="danger">
            {p.status === 'cancelled' && 'Кампания отменена.'}
            {p.status === 'failed' && 'Ошибка публикации.'}
            {p.status === 'failed_permissions' && 'У бота нет прав на публикацию в канале.'}
            {p.status === 'refunded' && 'Средства возвращены на баланс.'}
            {p.rejection_reason && (
              <span className="block mt-1 text-sm opacity-80">{p.rejection_reason}</span>
            )}
          </Notification>
        ) : isExpired && p.status === 'pending_owner' ? (
          <Notification type="danger">
            Срок ответа владельца истёк. Заявка #{p.id} будет автоматически отменена.
          </Notification>
        ) : (
          <Notification type={isPaid ? 'success' : 'info'}>
            {isPaid
              ? `Оплата получена — ожидаем публикации заявки #${p.id}.`
              : `Заявка #${p.id} отправлена владельцу канала.`}
          </Notification>
        )}
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
        <div className="bg-harbor-card border border-border rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-display text-[15px] font-semibold text-text-primary">
              Статус заявки
            </h3>
            <span className="text-[11px] text-text-tertiary">Обновляется автоматически</span>
          </div>
          <Timeline events={timelineEvents} />
        </div>

        <div className="bg-harbor-card border border-border rounded-xl p-5 h-fit">
          <div className="font-display text-[15px] font-semibold text-text-primary mb-3">
            Детали
          </div>
          <dl className="space-y-2.5 text-[13px]">
            <DetailRow icon="channels" label="Канал">
              @{p.channel?.username ?? `#${p.channel_id}`}
            </DetailRow>
            <DetailRow icon="docs" label="Формат">
              {formatInfo?.name ?? p.publication_format}
            </DetailRow>
            <DetailRow icon="ruble" label="Цена">
              <span className="font-mono font-semibold tabular-nums text-text-primary">
                {formatCurrency(p.final_price ?? p.counter_price ?? p.proposed_price)}
              </span>
            </DetailRow>
            <DetailRow icon="calendar" label="Дата">
              <span className="tabular-nums">
                {formatDateTimeMSK(p.final_schedule ?? p.proposed_schedule)}
              </span>
            </DetailRow>
          </dl>

          {!isTerminal && (
            <div className="mt-5 border-t border-border pt-4">
              <Button
                variant="danger"
                fullWidth
                loading={cancelling}
                iconLeft="close"
                onClick={handleCancel}
              >
                Отменить заявку
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function DetailRow({
  icon,
  label,
  children,
}: {
  icon: 'channels' | 'docs' | 'ruble' | 'calendar'
  label: string
  children: React.ReactNode
}) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="flex items-center gap-2 text-text-secondary">
        <Icon name={icon} size={13} className="text-text-tertiary" />
        {label}
      </span>
      <span className="text-text-primary text-right truncate">{children}</span>
    </div>
  )
}
