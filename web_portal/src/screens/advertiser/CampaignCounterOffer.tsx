/**
 * CampaignCounterOffer — Advertiser counter-offer screen (Web Portal).
 * FIX #20: Allows advertiser to reply with their own price to owner's counter-offer.
 */
import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
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
    return <div className="text-center py-8 text-gray-500">Загрузка...</div>
  }

  if (!placement) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
        Заявка не найдена
      </div>
    )
  }

  const ownerPrice = placement.counter_price ?? placement.proposed_price
  const maxRounds = 3
  const currentRound = placement.counter_offer_count + 1

  const handleSubmit = () => {
    const price = parseFloat(priceInput.replace(/\s/g, ''))
    if (isNaN(price) || price < 100) {
      setError('Минимальная цена — 100 ₽')
      return
    }

    updatePlacement(
      {
        id: placement.id,
        data: { action: 'counter-reply', price, comment: comment || undefined },
      },
      {
        onSuccess: () => {
          navigate(`/adv/campaigns/${placement.id}/waiting`)
        },
        onError: () => {
          setError('Не удалось отправить предложение. Попробуйте снова.')
        },
      },
    )
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-yellow-800">
        ✏️ Встречное предложение владельцу
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          {error}
        </div>
      )}

      {/* Current conditions card */}
      <div className="bg-white rounded-lg shadow p-6 space-y-4">
        <h2 className="text-lg font-semibold">📋 Текущие условия</h2>
        <div className="flex justify-between py-2 border-b">
          <span className="text-gray-600">💰 Цена владельца:</span>
          <span className="font-semibold">{formatCurrency(ownerPrice)}</span>
        </div>
        {placement.counter_comment && (
          <div className="py-2 border-b">
            <span className="text-gray-600">💬 Комментарий владельца:</span>
            <p className="mt-1 text-sm text-gray-500 italic">{placement.counter_comment}</p>
          </div>
        )}
        <div className="flex justify-between py-2">
          <span className="text-gray-600">📅 Раунд:</span>
          <span className="font-semibold">{currentRound}/{maxRounds}</span>
        </div>
      </div>

      {/* Price input */}
      <div className="bg-white rounded-lg shadow p-6 space-y-4">
        <label className="block">
          <span className="text-sm font-medium text-gray-700 uppercase tracking-wide">Ваша цена</span>
          <input
            type="number"
            className="mt-1 w-full px-4 py-3 text-lg border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="Введите цену (₽)"
            value={priceInput}
            onChange={(e) => {
              setPriceInput(e.target.value)
              setError(null)
            }}
            min={100}
            disabled={isPending}
          />
        </label>

        <label className="block">
          <span className="text-sm font-medium text-gray-700 uppercase tracking-wide">Комментарий (необязательно)</span>
          <textarea
            className="mt-1 w-full px-4 py-3 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-y"
            placeholder="Обоснуйте вашу цену..."
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            maxLength={500}
            rows={3}
            disabled={isPending}
          />
        </label>
      </div>

      {/* Action buttons */}
      <div className="space-y-3">
        <button
          type="button"
          className="w-full px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          onClick={handleSubmit}
          disabled={isPending || !priceInput}
        >
          {isPending ? '⏳ Отправка...' : '✏️ Отправить встречное предложение'}
        </button>

        <button
          type="button"
          className="w-full px-6 py-3 bg-gray-100 text-gray-700 font-medium rounded-lg hover:bg-gray-200 disabled:opacity-50"
          onClick={() => navigate(`/adv/campaigns/${placement.id}/payment`)}
          disabled={isPending}
        >
          ← Назад к оплате
        </button>
      </div>
    </div>
  )
}
