import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Card, Button, AmountChips, FeeBreakdown, Notification } from '@/components/ui'
import { MIN_WITHDRAWAL } from '@/lib/constants'
import { formatCurrency, calcWithdrawalFee } from '@/lib/formatters'
import { useHaptic } from '@/hooks/useHaptic'
import { useMe, useCreatePayout } from '@/hooks/queries'
import styles from './OwnPayoutRequest.module.css'

const PRESET_AMOUNTS = [1000, 3000, 5000, 10000]

export default function OwnPayoutRequest() {
  const navigate = useNavigate()
  const haptic = useHaptic()

  const { data: me } = useMe()
  const { mutate: createPayout, isPending } = useCreatePayout()

  const earnedRub = parseFloat(me?.earned_rub ?? '0')
  const [amount, setAmount] = useState(0)
  const [paymentDetails, setPaymentDetails] = useState('')

  const fee = calcWithdrawalFee(amount)

  const isValid =
    amount >= MIN_WITHDRAWAL &&
    amount <= earnedRub &&
    paymentDetails.length >= 5

  const handleSubmit = () => {
    haptic.success()
    createPayout(
      { amount, payment_details: paymentDetails },
      { onSuccess: () => navigate('/own/payouts') },
    )
  }

  return (
    <ScreenShell>
      <Card title="Доступно к выводу">
        <p className={styles.available}>{formatCurrency(earnedRub)}</p>
      </Card>

      <label className={styles.label}>Сумма вывода</label>

      <AmountChips
        amounts={PRESET_AMOUNTS}
        selected={PRESET_AMOUNTS.includes(amount) ? amount : undefined}
        onSelect={setAmount}
      />

      <button className={styles.allBtn} onClick={() => setAmount(earnedRub)}>
        Вывести всё ({formatCurrency(earnedRub)})
      </button>

      <input
        className={styles.input}
        type="number"
        placeholder="Введите сумму"
        value={amount === 0 ? '' : String(amount)}
        onChange={(e) => setAmount(parseFloat(e.target.value) || 0)}
      />

      {amount > 0 && (
        <FeeBreakdown
          rows={[
            { label: 'Запрашиваемая сумма', value: formatCurrency(fee.gross) },
            { label: 'Комиссия за перевод (1,5%)', value: `−${formatCurrency(fee.fee)}`, dim: true },
          ]}
          total={{ label: 'Будет переведено', value: formatCurrency(fee.net) }}
        />
      )}

      <label className={styles.label}>Реквизиты (номер карты / СБП)</label>
      <input
        className={styles.input}
        type="text"
        placeholder="Номер карты или телефон для СБП"
        value={paymentDetails}
        onChange={(e) => setPaymentDetails(e.target.value)}
      />

      <Notification type="info">
        <span style={{ fontSize: 'var(--rh-text-sm)' }}>
          ⏱ Обработка: до 24 часов · 09:00–22:00 МСК
        </span>
      </Notification>

      <Button fullWidth disabled={!isValid || isPending} onClick={handleSubmit}>
        {isPending ? '⏳ Отправка...' : '💸 Запросить вывод'}
      </Button>
    </ScreenShell>
  )
}
