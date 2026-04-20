import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Button,
  Notification,
  Skeleton,
  Textarea,
  Icon,
  ScreenHeader,
} from '@shared/ui'
import { usePlacementRequest, useUpdatePlacement } from '@/hooks/useCampaignQueries'
import { formatCurrency } from '@/lib/constants'

export default function CampaignCounterOffer() {
  const { id } = useParams<{ id: string }>()
  const numId = Number(id)
  const navigate = useNavigate()
  const [priceInput, setPriceInput] = useState('')
  const [comment, setComment] = useState('')
  const [error, setError] = useState<string | null>(null)

  const { data: placement, isLoading } = usePlacementRequest(isNaN(numId) ? null : numId)
  const { mutateAsync: updatePlacement, isPending } = useUpdatePlacement()

  if (isLoading) {
    return (
      <div className="max-w-[900px] mx-auto space-y-4">
        <Skeleton className="h-20" />
        <Skeleton className="h-40" />
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

  const ownerPrice = placement.counter_price ?? placement.proposed_price
  const maxRounds = 3
  const currentRound = placement.counter_offer_count + 1

  const numericProposal = parseFloat(priceInput.replace(/\s/g, ''))
  const delta =
    !isNaN(numericProposal) && ownerPrice
      ? numericProposal - Number(ownerPrice)
      : 0

  const handleSubmit = () => {
    const price = numericProposal
    if (isNaN(price) || price < 100) {
      setError('Минимальная цена — 100 ₽')
      return
    }

    void updatePlacement(
      { id: placement.id, data: { action: 'counter-reply', price, comment: comment || undefined } },
      {
        onSuccess: () => navigate(`/adv/campaigns/${placement.id}/waiting`),
        onError: () => setError('Не удалось отправить предложение. Попробуйте снова.'),
      },
    )
  }

  const channelLabel = `@${placement.channel?.username ?? `#${placement.channel_id}`}`

  return (
    <div className="max-w-[900px] mx-auto">
      <ScreenHeader
        title="Встречное предложение"
        subtitle={`${channelLabel} · раунд ${currentRound} из ${maxRounds}`}
        action={
          <Button
            variant="secondary"
            iconLeft="arrow-left"
            onClick={() => navigate(`/adv/campaigns/${placement.id}/payment`)}
          >
            К оплате
          </Button>
        }
      />

      {error && (
        <div className="mb-4">
          <Notification type="danger">{error}</Notification>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="bg-harbor-card border border-border rounded-xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <Icon name="users" size={14} className="text-text-tertiary" />
            <span className="font-display text-[14px] font-semibold text-text-primary">
              Предложение владельца
            </span>
          </div>
          <div className="bg-harbor-elevated rounded-lg p-4 mb-3">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-text-tertiary mb-1">
              Цена владельца
            </div>
            <div className="font-display text-[28px] font-bold tracking-[-0.02em] text-text-primary tabular-nums">
              {formatCurrency(ownerPrice)}
            </div>
          </div>
          {placement.counter_comment && (
            <div className="text-[13px] text-text-secondary bg-harbor-elevated rounded-md p-3 italic">
              «{placement.counter_comment}»
            </div>
          )}
          <div className="mt-3 text-[12px] text-text-tertiary flex items-center gap-2">
            <Icon name="hourglass" size={12} />
            Раунд {currentRound} из {maxRounds}
          </div>
        </div>

        <div className="bg-harbor-card border border-border rounded-xl p-5 relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-[3px] bg-gradient-to-r from-accent to-accent-2" />
          <div className="flex items-center gap-2 mb-3">
            <Icon name="edit" size={14} className="text-accent" />
            <span className="font-display text-[14px] font-semibold text-text-primary">
              Ваше встречное
            </span>
          </div>

          <label className="block">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-text-tertiary">
              Цена (₽)
            </span>
            <input
              type="number"
              className="mt-1.5 w-full px-4 py-3 font-display font-bold text-[22px] tracking-[-0.02em] tabular-nums bg-harbor-elevated border border-border rounded-lg text-text-primary focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/25"
              placeholder="Например, 8500"
              value={priceInput}
              onChange={(e) => {
                setPriceInput(e.target.value)
                setError(null)
              }}
              min={100}
              disabled={isPending}
            />
          </label>

          {!isNaN(numericProposal) && numericProposal > 0 && ownerPrice && (
            <div className="mt-2 text-[12.5px] flex items-center gap-1.5">
              <Icon
                name={delta < 0 ? 'arrow-down' : delta > 0 ? 'arrow-up' : 'check'}
                size={12}
                className={delta < 0 ? 'text-success' : delta > 0 ? 'text-warning' : 'text-text-tertiary'}
              />
              <span className={delta < 0 ? 'text-success' : delta > 0 ? 'text-warning' : 'text-text-tertiary'}>
                {delta === 0
                  ? 'Равна цене владельца'
                  : `${delta > 0 ? '+' : ''}${formatCurrency(Math.abs(delta))} к цене владельца`}
              </span>
            </div>
          )}

          <div className="mt-4">
            <label className="block">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-text-tertiary">
                Комментарий (необязательно)
              </span>
              <Textarea
                rows={3}
                value={comment}
                onChange={setComment}
                placeholder="Обоснуйте вашу цену…"
                maxLength={500}
              />
            </label>
          </div>
        </div>
      </div>

      <div className="mt-5 flex flex-col sm:flex-row gap-3">
        <Button
          variant="primary"
          iconLeft="refresh"
          onClick={handleSubmit}
          loading={isPending}
          disabled={!priceInput}
        >
          Отправить встречное предложение
        </Button>
        <Button
          variant="secondary"
          iconLeft="arrow-left"
          onClick={() => navigate(`/adv/campaigns/${placement.id}/payment`)}
        >
          Назад к оплате
        </Button>
      </div>
    </div>
  )
}
