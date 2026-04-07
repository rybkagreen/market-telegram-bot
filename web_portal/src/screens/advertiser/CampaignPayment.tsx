import { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { Card, Notification, Button, Skeleton } from '@shared/ui'
import { formatCurrency } from '@/lib/constants'
import { usePlacementRequest, useUpdatePlacement } from '@/hooks/useCampaignQueries'
import { useContracts } from '@/hooks/queries'

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

  const isExpired = placement?.expires_at ? new Date(placement.expires_at) < new Date() : false
  const isCounterOffer = placement?.status === 'counter_offer'
  const formatInfo = placement?.publication_format
    ? PUBLICATION_FORMATS[placement.publication_format]
    : { name: 'Неизвестно', multiplier: 1.0 }
  const price = placement?.final_price ?? placement?.proposed_price ?? '0'
  const platformCommission = placement?.final_price
    ? (parseFloat(placement.final_price) * 0.15).toFixed(2)
    : '—'
  const ownerPayout = placement?.final_price
    ? (parseFloat(placement.final_price) * 0.85).toFixed(2)
    : '—'

  // Redirect based on status
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
  }, [placement?.status, isExpired])

  // Check framework contract
  useEffect(() => {
    if (!contractsLoading && contractsList && placement && !placement.is_test) {
      const hasSigned = contractsList.items.some(
        (c) => c.contract_type === 'advertiser_framework' && c.contract_status === 'signed',
      )
      if (!hasSigned) {
        navigate(`/contracts/framework?returnTo=/adv/campaigns/${numId}/payment`, { replace: true })
      }
    }
  }, [contractsList, contractsLoading, placement, navigate, numId])

  if (isLoading || contractsLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-20" />
        <Skeleton className="h-48" />
        <Skeleton className="h-12" />
      </div>
    )
  }

  if (!placement) {
    return <Notification type="danger">Заявка не найдена</Notification>
  }

  const frameworkContract = contractsList?.items.find(
    (c) => c.contract_type === 'advertiser_framework' && c.contract_status === 'signed',
  )
  const frameworkRef = frameworkContract
    ? `рамочному договору №${frameworkContract.id} от ${new Date(frameworkContract.signed_at!).toLocaleDateString('ru-RU')}`
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
            navigate(`/adv/campaigns/${placement.id}/waiting`)
          }
        },
        onError: (err) => {
          hasSubmitted.current = false
          const status = (err as { response?: { status?: number } })?.response?.status
          if (status === 409) {
            queryClient.invalidateQueries({ queryKey: ['placement-request', placement.id] })
            setSubmitError('Статус заявки изменился. Страница будет обновлена.')
          } else {
            setSubmitError('Произошла ошибка. Попробуйте ещё раз.')
          }
        },
      },
    )
  }

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Page title */}
      <div>
        <h1 className="text-2xl font-display font-bold text-text-primary">Оплата размещения</h1>
        <p className="text-text-secondary mt-1">
          Канал: @{placement.channel?.username ?? `#${placement.channel_id}`} · {formatInfo.name}
        </p>
      </div>

      {/* Status */}
      {isCounterOffer ? (
        <Notification type="warning">✏️ Владелец предложил другие условия</Notification>
      ) : (
        <Notification type="success">✅ Владелец принял условия!</Notification>
      )}

      {/* Counter offer details */}
      {isCounterOffer && (
        <Card title="Контрпредложение владельца">
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-text-secondary">Оригинальная цена:</span>
              <span className="line-through text-text-tertiary">{formatCurrency(placement.proposed_price)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-secondary">Новая цена:</span>
              <span className="text-lg font-bold text-accent">{formatCurrency(price)}</span>
            </div>
            {placement.counter_comment && (
              <div className="bg-harbor-elevated rounded-md p-3 text-sm text-text-secondary">
                {placement.counter_comment}
              </div>
            )}
          </div>
        </Card>
      )}

      {/* Fee breakdown */}
      <Card title="Детали оплаты">
        <div className="space-y-3">
          <div className="flex justify-between text-sm">
            <span className="text-text-secondary">Стоимость размещения</span>
            <span className="font-mono text-text-primary">{formatCurrency(price)}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-text-secondary">Комиссия платформы (15%)</span>
            <span className="font-mono text-text-secondary">{formatCurrency(platformCommission)}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-text-secondary">К выплате владельцу (85%)</span>
            <span className="font-mono text-text-secondary">{formatCurrency(ownerPayout)}</span>
          </div>
          <div className="border-t border-border pt-3">
            <div className="flex justify-between">
              <span className="font-semibold text-text-primary">Итого к оплате</span>
              <span className="font-mono text-xl font-bold text-text-primary">{formatCurrency(price)}</span>
            </div>
          </div>
        </div>
      </Card>

      {/* Expiry notice */}
      {placement.expires_at && (
        <Notification type="info">
          ⏱ Действует до {new Date(placement.expires_at).toLocaleString('ru-RU')} (24 ч)
        </Notification>
      )}

      {/* Submit error */}
      {submitError && (
        <Notification type="danger">{submitError}</Notification>
      )}

      {/* Contract notice */}
      <Notification type="info">
        📄 Нажимая «Оплатить», вы подтверждаете размещение рекламы согласно {frameworkRef}.
      </Notification>

      {/* Action buttons */}
      <div className="flex flex-col gap-3">
        {isCounterOffer && (
          <Button
            variant="secondary"
            fullWidth
            loading={isPending}
            onClick={() => handleAction('accept-counter')}
          >
            {isPending ? '⏳ Принятие...' : '✏️ Принять контрпредложение'}
          </Button>
        )}

        <Button
          variant="primary"
          fullWidth
          loading={isPending}
          onClick={() => handleAction('pay')}
        >
          {isPending ? '⏳ Оплата...' : '💳 Оплатить и запустить кампанию'}
        </Button>

        <Button
          variant="danger"
          fullWidth
          loading={isPending}
          onClick={() => handleAction('cancel')}
        >
          ❌ Отменить заявку
        </Button>

        <Button variant="ghost" fullWidth onClick={() => navigate('/adv')}>
          ← В меню рекламодателя
        </Button>
      </div>

      <Notification type="warning">
        ⚠️ Отмена после оплаты: возврат 50%
      </Notification>
    </div>
  )
}
