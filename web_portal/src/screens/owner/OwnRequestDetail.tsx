import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import {
  Notification,
  Button,
  Skeleton,
  Timeline,
  Icon,
  ScreenHeader,
  Textarea,
  FeeBreakdown,
} from '@shared/ui'
import { formatCurrency, formatDateTimeMSK } from '@/lib/constants'
import { usePlacementRequest, useUpdatePlacement } from '@/hooks/useCampaignQueries'

export default function OwnRequestDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const numId = id ? parseInt(id, 10) : null

  const { data: request, isLoading } = usePlacementRequest(numId)
  const { mutate: updatePlacement, isPending } = useUpdatePlacement()
  const queryClient = useQueryClient()

  const [counterPrice, setCounterPrice] = useState('')
  const [counterDate, setCounterDate] = useState('')
  const [counterTime, setCounterTime] = useState('14:00')
  const [rejectionText, setRejectionText] = useState('')

  if (isLoading) {
    return (
      <div className="max-w-[1080px] mx-auto space-y-4">
        <Skeleton className="h-20" />
        <Skeleton className="h-64" />
      </div>
    )
  }

  if (!request) {
    return (
      <div className="max-w-[1080px] mx-auto">
        <Notification type="danger">Заявка не найдена</Notification>
      </div>
    )
  }

  const formatNames: Record<string, string> = {
    post_24h: 'Пост 24ч',
    post_48h: 'Пост 48ч',
    post_7d: 'Пост 7д',
    pin_24h: 'Закреп 24ч',
    pin_48h: 'Закреп 48ч',
  }
  const fmtName = formatNames[request.publication_format] ?? request.publication_format
  const isExpired = request.expires_at ? new Date(request.expires_at) < new Date() : false
  const isPaid = request.status === 'escrow' || request.status === 'published'
  const isPublished = request.status === 'published'

  const timelineEvents = [
    {
      id: 'created',
      icon: '',
      title: 'Заявка создана',
      subtitle: formatDateTimeMSK(request.created_at),
      variant: 'success' as const,
    },
    request.status === 'pending_owner'
      ? {
          id: 'waiting_owner',
          icon: '',
          title: isExpired ? 'Срок ответа истёк' : 'Ожидает вашего решения',
          subtitle: isExpired
            ? 'Заявка просрочена'
            : `Действует до ${formatDateTimeMSK(request.expires_at)}`,
          variant: isExpired ? ('danger' as const) : ('warning' as const),
        }
      : request.status === 'counter_offer'
        ? {
            id: 'counter_sent',
            icon: '',
            title: 'Контр-предложение отправлено',
            subtitle: `Ожидание ответа рекламодателя до ${formatDateTimeMSK(request.expires_at)}`,
            variant: 'warning' as const,
          }
        : {
            id: 'accepted',
            icon: '',
            title: 'Заявка принята',
            subtitle: formatDateTimeMSK(request.created_at),
            variant: 'success' as const,
          },
    {
      id: 'payment',
      icon: '',
      title: isPaid ? 'Оплачено' : 'Оплата',
      subtitle: isPaid ? 'Средства в эскроу' : 'После принятия заявки',
      variant: isPaid ? ('success' as const) : ('default' as const),
    },
    {
      id: 'published',
      icon: '',
      title: isPublished ? 'Опубликовано' : 'Публикация',
      subtitle: request.published_at
        ? formatDateTimeMSK(request.published_at)
        : request.final_schedule
          ? formatDateTimeMSK(request.final_schedule)
          : 'Запланировано',
      variant: isPublished ? ('success' as const) : ('default' as const),
    },
    request.status === 'cancelled'
      ? {
          id: 'cancelled',
          icon: '',
          title: 'Отклонено',
          subtitle: request.rejection_reason || 'Без причины',
          variant: 'danger' as const,
        }
      : null,
  ].filter((e): e is NonNullable<typeof e> => e !== null)

  const handleAccept = () => {
    updatePlacement(
      { id: request.id, data: { action: 'accept' } },
      { onSuccess: () => navigate('/own/requests') },
    )
  }

  const handleCounter = () => {
    const price = parseFloat(counterPrice) || parseFloat(request.proposed_price)
    const schedule = counterDate && counterTime ? `${counterDate}T${counterTime}:00` : undefined
    updatePlacement(
      { id: request.id, data: { action: 'counter', price, schedule } },
      {
        onSuccess: () => navigate('/own/requests'),
        onError: () =>
          queryClient.invalidateQueries({ queryKey: ['placement-request', numId] }),
      },
    )
  }

  const handleReject = () => {
    updatePlacement(
      { id: request.id, data: { action: 'reject', comment: rejectionText } },
      { onSuccess: () => navigate('/own/requests') },
    )
  }

  const statusBanner = () => {
    if (isExpired && request.status === 'pending_owner') {
      return <Notification type="danger">Срок ответа истёк. Заявка скоро будет отменена.</Notification>
    }
    if (request.status === 'pending_payment') {
      return <Notification type="warning">Ожидаем оплаты от рекламодателя.</Notification>
    }
    if (request.status === 'escrow') {
      return <Notification type="success">Оплата получена. Публикация запланирована.</Notification>
    }
    if (request.status === 'counter_offer') {
      return <Notification type="info">Ожидаем ответа рекламодателя на контрпредложение.</Notification>
    }
    return null
  }

  const price = parseFloat(request.proposed_price)
  const ownerShare = price * 0.85

  return (
    <div className="max-w-[1080px] mx-auto">
      <ScreenHeader
        title={`Заявка #${request.id}`}
        subtitle={`@${request.channel?.username ?? `#${request.channel_id}`} · ${fmtName}`}
        action={
          <Button
            variant="secondary"
            iconLeft="arrow-left"
            onClick={() => navigate('/own/requests')}
          >
            К списку
          </Button>
        }
      />

      {statusBanner() && <div className="mb-5">{statusBanner()}</div>}

      <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
        <div className="space-y-4">
          <div className="bg-harbor-card border border-border rounded-xl p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-display text-[15px] font-semibold text-text-primary">
                Хронология
              </h3>
            </div>
            <Timeline events={timelineEvents} />
          </div>

          <div className="bg-harbor-card border border-border rounded-xl p-5">
            <div className="flex items-center gap-2 mb-3">
              <Icon name="docs" size={14} className="text-text-tertiary" />
              <span className="font-display text-[14px] font-semibold text-text-primary">
                Текст объявления
              </span>
            </div>
            <p className="text-[13.5px] leading-[1.55] text-text-secondary whitespace-pre-wrap">
              {request.ad_text}
            </p>
          </div>

          {request.status === 'pending_owner' && !isExpired && (
            <>
              <div className="bg-harbor-card border border-border rounded-xl p-5">
                <div className="flex items-center gap-2 mb-3">
                  <Icon name="refresh" size={14} className="text-accent-2" />
                  <span className="font-display text-[14px] font-semibold text-text-primary">
                    Контр-предложение
                  </span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <InputField label="Цена">
                    <input
                      type="number"
                      className="w-full px-3 py-2 rounded-md border border-border bg-harbor-elevated text-text-primary font-mono tabular-nums focus:outline-none focus:ring-2 focus:ring-accent/25 focus:border-accent"
                      value={counterPrice || request.proposed_price}
                      onChange={(e) => setCounterPrice(e.target.value)}
                    />
                  </InputField>
                  <InputField label="Дата">
                    <input
                      type="date"
                      className="w-full px-3 py-2 rounded-md border border-border bg-harbor-elevated text-text-primary focus:outline-none focus:ring-2 focus:ring-accent/25 focus:border-accent"
                      value={counterDate}
                      onChange={(e) => setCounterDate(e.target.value)}
                    />
                  </InputField>
                  <InputField label="Время">
                    <input
                      type="time"
                      className="w-full px-3 py-2 rounded-md border border-border bg-harbor-elevated text-text-primary focus:outline-none focus:ring-2 focus:ring-accent/25 focus:border-accent"
                      value={counterTime}
                      onChange={(e) => setCounterTime(e.target.value)}
                    />
                  </InputField>
                </div>
                <Button
                  variant="secondary"
                  iconLeft="refresh"
                  className="mt-3"
                  loading={isPending}
                  onClick={handleCounter}
                >
                  Отправить контр-предложение
                </Button>
              </div>

              <div className="bg-harbor-card border border-danger/25 rounded-xl p-5">
                <div className="flex items-center gap-2 mb-3">
                  <Icon name="close" size={14} className="text-danger" />
                  <span className="font-display text-[14px] font-semibold text-text-primary">
                    Отклонить
                  </span>
                </div>
                <Textarea
                  rows={3}
                  value={rejectionText}
                  onChange={setRejectionText}
                  placeholder="Причина отклонения (минимум 10 символов)"
                />
                <p className="text-[11.5px] text-warning mt-2 flex items-center gap-1.5">
                  <Icon name="warning" size={12} />
                  Необоснованный отказ: −10 к репутации
                </p>
                <Button
                  variant="danger"
                  iconLeft="close"
                  className="mt-3"
                  disabled={rejectionText.length < 10 || isPending}
                  onClick={handleReject}
                >
                  Отклонить заявку
                </Button>
              </div>
            </>
          )}

          {request.status === 'cancelled' && request.rejection_reason && (
            <div className="bg-harbor-card border border-border rounded-xl p-5">
              <div className="flex items-center gap-2 mb-2">
                <Icon name="close" size={14} className="text-danger" />
                <span className="font-display text-[14px] font-semibold text-text-primary">
                  Причина отклонения
                </span>
              </div>
              <p className="text-[13.5px] text-text-secondary">{request.rejection_reason}</p>
            </div>
          )}
        </div>

        <div className="space-y-4">
          <div className="bg-harbor-card border border-border rounded-xl p-5 h-fit">
            <div className="font-display text-[14px] font-semibold text-text-primary mb-3">
              Условия
            </div>
            <FeeBreakdown
              rows={[
                { label: 'Цена рекламодателя', value: formatCurrency(price) },
                { label: 'Комиссия платформы (15%)', value: formatCurrency(price * 0.15) },
              ]}
              total={{ label: 'Ваша выплата (85%)', value: formatCurrency(ownerShare) }}
            />
          </div>

          {request.status === 'pending_owner' && !isExpired && (
            <div className="bg-harbor-card border border-border rounded-xl p-5 h-fit flex flex-col gap-2.5">
              <div className="font-display text-[14px] font-semibold text-text-primary mb-1">
                Действия
              </div>
              <Button variant="primary" iconLeft="check" fullWidth loading={isPending} onClick={handleAccept}>
                Принять условия
              </Button>
              <p className="text-[11.5px] text-text-tertiary">
                Или отправьте контр-оферту / отклоните заявку ниже.
              </p>
            </div>
          )}

          {request.status === 'published' && request.published_at && (
            <div className="bg-harbor-card border border-success/25 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-2">
                <Icon name="check" size={14} className="text-success" />
                <span className="font-display text-[14px] font-semibold text-text-primary">
                  Опубликовано
                </span>
              </div>
              <div className="text-[13px] text-text-secondary">
                {formatDateTimeMSK(request.published_at)}
              </div>
              <div className="mt-2 text-[13px] text-success font-mono tabular-nums font-semibold">
                +{formatCurrency(ownerShare)} на баланс
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function InputField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="block text-[11px] font-semibold uppercase tracking-wider text-text-tertiary mb-1">
        {label}
      </span>
      {children}
    </label>
  )
}
