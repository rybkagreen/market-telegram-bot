/**
 * CampaignCounterOffer — Advertiser counter-offer screen.
 * FIX #20: Allows advertiser to reply with their own price to owner's counter-offer.
 */
import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Notification } from '@/components/ui/Notification'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { useHaptic } from '@/hooks/useHaptic'
import { usePlacement, useUpdatePlacement } from '@/hooks/queries'
import { formatCurrency } from '@/lib/formatters'
import styles from './CampaignCounterOffer.module.css'

export default function CampaignCounterOffer() {
  const { id } = useParams<{ id: string }>()
  const numId = Number(id)
  const navigate = useNavigate()
  const haptic = useHaptic()
  const [priceInput, setPriceInput] = useState('')
  const [comment, setComment] = useState('')
  const [error, setError] = useState<string | null>(null)

  const { data: placement, isLoading } = usePlacement(isNaN(numId) ? null : numId)
  const { mutateAsync: updatePlacement, isPending } = useUpdatePlacement()

  if (isLoading) {
    return (
      <ScreenShell>
        <div className={styles.loading}>Загрузка...</div>
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

  const ownerPrice = placement.counter_price ?? placement.proposed_price
  const ownerPriceFormatted = formatCurrency(ownerPrice)
  const maxRounds = 3
  const currentRound = placement.counter_offer_count + 1

  const handleSubmit = () => {
    if (isPending) return
    const price = parseFloat(priceInput.replace(/\s/g, ''))
    if (isNaN(price) || price < 100) {
      setError('Минимальная цена — 100 ₽')
      return
    }

    haptic.success()

    updatePlacement(
      {
        id: placement!.id,
        data: { action: 'counter-reply', price, comment: comment || undefined },
      },
      {
        onSuccess: () => {
          navigate(`/adv/campaigns/${placement!.id}/waiting`)
        },
        onError: (err: unknown) => {
          if ((err as { response?: { status?: number } })?.response?.status === 409) {
            setError('Статус заявки изменился, страница обновлена')
          } else {
            setError('Не удалось отправить предложение. Попробуйте снова.')
          }
        },
      },
    )
  }

  return (
    <ScreenShell>
      <Notification type="warning">
        ✏️ Встречное предложение владельцу
      </Notification>

      {error && <Notification type="danger">{error}</Notification>}

      <Card title="📋 Текущие условия" className={styles.card}>
        <div className={styles.row}>
          <span className={styles.label}>💰 Цена владельца:</span>
          <span className={styles.value}>{ownerPriceFormatted}</span>
        </div>
        {placement.counter_comment && (
          <div className={styles.commentRow}>
            <span className={styles.label}>💬 Комментарий владельца:</span>
            <p className={styles.comment}>{placement.counter_comment}</p>
          </div>
        )}
        <div className={styles.row}>
          <span className={styles.label}>📅 Раунд:</span>
          <span className={styles.value}>{currentRound}/{maxRounds}</span>
        </div>
      </Card>

      <p className={styles.sectionTitle}>Ваша цена</p>
      <input
        type="number"
        className={styles.input}
        placeholder="Введите цену (₽)"
        value={priceInput}
        onChange={(e) => {
          setPriceInput(e.target.value)
          setError(null)
        }}
        min={100}
        disabled={isPending}
      />

      <p className={styles.sectionTitle}>Комментарий (необязательно)</p>
      <textarea
        className={styles.textarea}
        placeholder="Обоснуйте вашу цену..."
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        maxLength={500}
        rows={3}
        disabled={isPending}
      />

      <div className={styles.buttons}>
        <Button
          variant="primary"
          fullWidth
          disabled={isPending || !priceInput}
          onClick={handleSubmit}
        >
          {isPending ? '⏳ Отправка...' : '✏️ Отправить встречное предложение'}
        </Button>

        <Button
          variant="secondary"
          fullWidth
          onClick={() => navigate(`/adv/campaigns/${placement.id}/payment`)}
          disabled={isPending}
        >
          ← Назад к оплате
        </Button>
      </div>
    </ScreenShell>
  )
}
