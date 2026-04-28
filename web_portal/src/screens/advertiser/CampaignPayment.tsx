import { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import {
  Notification,
  Button,
  Skeleton,
  FeeBreakdown,
  Icon,
  ScreenHeader,
} from '@shared/ui'
import {
  CANCEL_REFUND_ADVERTISER,
  CANCEL_REFUND_OWNER,
  CANCEL_REFUND_PLATFORM,
  OWNER_NET_RATE,
  PLATFORM_COMMISSION_GROSS,
  PLATFORM_TOTAL_RATE,
  SERVICE_FEE,
  computePlacementSplit,
  formatCurrency,
  formatDateMSK,
  formatDateTimeMSK,
  formatRatePct,
} from '@/lib/constants'
import { usePlacementRequest, useUpdatePlacement } from '@/hooks/useCampaignQueries'
import { useContracts } from '@/hooks/queries'
import { useToast } from '@/hooks/useToast'

const PUBLICATION_FORMATS: Record<string, { name: string; multiplier: number }> = {
  post_24h: { name: 'Пост 24ч', multiplier: 1.0 },
  post_48h: { name: 'Пост 48ч', multiplier: 1.4 },
  post_7d: { name: 'Пост 7д', multiplier: 2.0 },
  pin_24h: { name: 'Закреп 24ч', multiplier: 3.0 },
  pin_48h: { name: 'Закреп 48ч', multiplier: 4.0 },
}

export default function CampaignPayment() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const numId = id ? parseInt(id, 10) : null

  const { data: placement, isLoading } = usePlacementRequest(numId)
  const { mutate: updatePlacement, isPending } = useUpdatePlacement()
  const { data: contractsList, isLoading: contractsLoading } = useContracts('advertiser_framework')
  const queryClient = useQueryClient()
  const hasSubmitted = useRef(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const { showToast, ToastComponent } = useToast()

  const isExpired = placement?.expires_at ? new Date(placement.expires_at) < new Date() : false
  const isCounterOffer = placement?.status === 'counter_offer'
  const formatInfo = placement?.publication_format
    ? PUBLICATION_FORMATS[placement.publication_format]
    : { name: 'Неизвестно', multiplier: 1.0 }

  const priceNum = (() => {
    const raw = placement?.final_price ?? placement?.counter_price ?? placement?.proposed_price
    if (raw == null) return 0
    const n = parseFloat(String(raw))
    return isNaN(n) ? 0 : n
  })()
  const price = priceNum
  // Промт 15.7: derive split via computePlacementSplit from shared constants.
  const split = computePlacementSplit(priceNum)
  const platformGrossCommission = split.platformGross
  const serviceFee = split.serviceFee
  const platformCommission = split.platformTotal
  const ownerPayout = split.ownerNet

  useEffect(() => {
    if (!placement) return
    if (placement.status === 'escrow') {
      navigate(`/adv/campaigns/${placement.id}/waiting`, { replace: true })
    }
    if (placement.status === 'published') {
      navigate(`/adv/campaigns/${placement.id}/published`, { replace: true })
    }
    if (['cancelled', 'failed', 'refunded'].includes(placement.status)) {
      navigate('/adv/campaigns', { replace: true })
    }
    if (isExpired && ['pending_payment', 'counter_offer'].includes(placement.status)) {
      navigate('/adv/campaigns', { replace: true })
    }
  }, [placement?.status, isExpired, navigate])

  useEffect(() => {
    if (!contractsLoading && contractsList && placement && !placement.is_test) {
      const hasSigned = contractsList.items.some(
        (c) => c.contract_type === 'advertiser_framework' && c.contract_status === 'signed',
      )
      if (!hasSigned) {
        navigate(`/contracts/framework?returnTo=/adv/campaigns/${numId}/payment`, {
          replace: true,
        })
      }
    }
  }, [contractsList, contractsLoading, placement, navigate, numId])

  if (isLoading || contractsLoading) {
    return (
      <div className="max-w-[900px] mx-auto space-y-4">
        <Skeleton className="h-20" />
        <Skeleton className="h-48" />
        <Skeleton className="h-12" />
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

  const frameworkContract = contractsList?.items.find(
    (c) => c.contract_type === 'advertiser_framework' && c.contract_status === 'signed',
  )
  const frameworkRef = frameworkContract
    ? `рамочному договору №${frameworkContract.id} от ${formatDateMSK(frameworkContract.signed_at!)}`
    : 'рамочному договору'

  const handleAction = (action: string) => {
    if (hasSubmitted.current) return
    hasSubmitted.current = true
    setSubmitError(null)

    updatePlacement(
      { id: placement.id, data: { action } },
      {
        onSuccess: () => {
          if (action === 'cancel') {
            navigate('/adv/campaigns')
          } else {
            showToast('Оплата прошла успешно. Ожидайте подтверждения владельца.', 'success')
            setTimeout(() => navigate(`/adv/campaigns/${placement.id}/waiting`), 1500)
          }
        },
        onError: (err) => {
          hasSubmitted.current = false
          const status = (err as { response?: { status?: number } })?.response?.status
          if (status === 409) {
            queryClient.invalidateQueries({ queryKey: ['placement-request', placement.id] })
            setSubmitError('Статус заявки изменился. Страница будет обновлена.')
          } else {
            showToast('Ошибка оплаты. Попробуйте ещё раз.', 'error')
          }
        },
      },
    )
  }

  const channelLabel = `@${placement.channel?.username ?? `#${placement.channel_id}`}`

  return (
    <div className="max-w-[900px] mx-auto">
      <ScreenHeader
        title="Оплата размещения"
        subtitle={`${channelLabel} · ${formatInfo.name}`}
        action={
          <Button
            variant="secondary"
            size="sm"
            iconLeft="arrow-left"
            onClick={() => navigate('/adv/campaigns')}
          >
            К списку
          </Button>
        }
      />

      <div className="mb-5">
        {isCounterOffer ? (
          <Notification type="warning">Владелец предложил другие условия размещения.</Notification>
        ) : (
          <Notification type="success">Владелец принял ваши условия.</Notification>
        )}
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
        <div className="space-y-4">
          <div className="bg-harbor-card border border-border rounded-xl p-5 relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-[3px] bg-gradient-to-r from-accent to-accent-2" />
            <div className="text-[11px] font-semibold uppercase tracking-wider text-text-tertiary mb-1">
              Итого к оплате
            </div>
            <div className="font-display text-[34px] font-bold tracking-[-0.02em] text-text-primary tabular-nums">
              {formatCurrency(price)}
            </div>
            <div className="text-[12.5px] text-text-tertiary mt-1">
              Средства будут зарезервированы на эскроу-счёте до подтверждения публикации.
            </div>
          </div>

          {isCounterOffer && (
            <div className="bg-harbor-card border border-border rounded-xl p-5">
              <div className="flex items-center gap-2 mb-3">
                <Icon name="refresh" size={14} className="text-accent-2" />
                <span className="font-display text-[14px] font-semibold text-text-primary">
                  Контрпредложение владельца
                </span>
              </div>
              <div className="grid grid-cols-2 gap-4 mb-3">
                <div className="bg-harbor-elevated rounded-lg p-3">
                  <div className="text-[11px] text-text-tertiary mb-1">Было</div>
                  <div className="font-mono tabular-nums text-text-secondary line-through text-[14px]">
                    {formatCurrency(placement.proposed_price)}
                  </div>
                </div>
                <div className="bg-accent-muted/40 border border-accent/25 rounded-lg p-3">
                  <div className="text-[11px] text-accent mb-1 font-semibold">Стало</div>
                  <div className="font-mono tabular-nums text-accent font-bold text-[14px]">
                    {formatCurrency(price)}
                  </div>
                </div>
              </div>
              {placement.counter_comment && (
                <div className="text-[13px] text-text-secondary bg-harbor-elevated rounded-md p-3 italic">
                  «{placement.counter_comment}»
                </div>
              )}
            </div>
          )}

          <div className="bg-harbor-card border border-border rounded-xl p-5">
            <div className="font-display text-[14px] font-semibold text-text-primary mb-3">
              Детали оплаты
            </div>
            <FeeBreakdown
              rows={[
                { label: 'Стоимость размещения', value: formatCurrency(price) },
                {
                  label: `Комиссия платформы (${formatRatePct(PLATFORM_COMMISSION_GROSS, 0)})`,
                  value: formatCurrency(platformGrossCommission),
                },
                {
                  label: `Сервисный сбор ${formatRatePct(SERVICE_FEE)} (из доли владельца)`,
                  value: formatCurrency(serviceFee),
                },
                {
                  label: `Итого удержано платформой (${formatRatePct(PLATFORM_TOTAL_RATE)})`,
                  value: formatCurrency(platformCommission),
                },
                {
                  label: `К выплате владельцу (${formatRatePct(OWNER_NET_RATE)})`,
                  value: formatCurrency(ownerPayout),
                },
              ]}
              total={{ label: 'Итого к оплате', value: formatCurrency(price) }}
            />
          </div>

          {placement.expires_at && (
            <Notification type="info">
              Действительно до {formatDateTimeMSK(placement.expires_at)} (24 ч).
            </Notification>
          )}

          {submitError && <Notification type="danger">{submitError}</Notification>}

          <Notification type="info">
            Нажимая «Оплатить», вы подтверждаете размещение согласно {frameworkRef}.
          </Notification>

          <Notification type="warning">
            Отмена после подтверждения и до публикации (Промт 15.7):{' '}
            {formatRatePct(CANCEL_REFUND_ADVERTISER, 0)} возврат рекламодателю /{' '}
            {formatRatePct(CANCEL_REFUND_OWNER, 0)} владельцу /{' '}
            {formatRatePct(CANCEL_REFUND_PLATFORM, 0)} платформе.
          </Notification>
        </div>

        <div className="bg-harbor-card border border-border rounded-xl p-5 h-fit flex flex-col gap-2.5">
          <div className="font-display text-[14px] font-semibold text-text-primary mb-1">
            Действия
          </div>
          {isCounterOffer && (
            <Button
              variant="secondary"
              fullWidth
              iconLeft="refresh"
              loading={isPending}
              onClick={() => navigate(`/adv/campaigns/${numId}/counter-offer`)}
            >
              Встречное предложение
            </Button>
          )}
          <Button
            variant="primary"
            fullWidth
            iconLeft="card"
            loading={isPending}
            onClick={() => handleAction(isCounterOffer ? 'accept-counter' : 'pay')}
          >
            {isCounterOffer ? 'Принять и оплатить' : 'Оплатить и запустить'}
          </Button>
          <Button
            variant="danger"
            fullWidth
            iconLeft="close"
            loading={isPending}
            onClick={() => handleAction('cancel')}
          >
            Отменить заявку
          </Button>
          <Button variant="ghost" fullWidth onClick={() => navigate('/adv')}>
            В меню рекламодателя
          </Button>
        </div>
      </div>

      {ToastComponent}
    </div>
  )
}
