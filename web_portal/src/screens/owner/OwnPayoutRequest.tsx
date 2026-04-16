import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Button, Notification } from '@shared/ui'
import { formatCurrency } from '@/lib/constants'
import { useMe } from '@/hooks/queries'
import { useCreatePayout } from '@/hooks/usePayoutQueries'

const MIN_WITHDRAWAL = 1000
const PAYOUT_FEE_RATE = 0.015
const PRESET_AMOUNTS = [1000, 3000, 5000, 10000]

export default function OwnPayoutRequest() {
  const navigate = useNavigate()
  const { data: me } = useMe()
  const { mutate: createPayout, isPending } = useCreatePayout()

  const earnedRub = parseFloat(me?.earned_rub ?? '0')
  const [amount, setAmount] = useState(0)
  const [paymentDetails, setPaymentDetails] = useState('')

  const fee = amount * PAYOUT_FEE_RATE
  const netAmount = amount - fee

  const isValid =
    amount >= MIN_WITHDRAWAL &&
    amount <= earnedRub &&
    paymentDetails.length >= 5

  const handleSubmit = () => {
    createPayout(
      { gross_amount: amount, requisites: paymentDetails },
      { onSuccess: () => navigate('/own/payouts') },
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-display font-bold text-text-primary">Запросить вывод</h1>

      {/* Available balance */}
      <Card title="Доступно к выводу">
        <p className="text-3xl font-bold text-success">{formatCurrency(earnedRub)}</p>
      </Card>

      {/* Amount */}
      <Card title="Сумма вывода">
        <div className="flex gap-2 flex-wrap mb-3">
          {PRESET_AMOUNTS.map((a) => (
            <button
              key={a}
              className={`px-3 py-1.5 rounded-full text-sm font-medium border transition-all ${
                amount === a
                  ? 'border-accent bg-accent-muted text-accent'
                  : 'border-border bg-harbor-elevated text-text-secondary hover:border-accent/50'
              }`}
              onClick={() => setAmount(a)}
            >
              {a.toLocaleString('ru-RU')} ₽
            </button>
          ))}
          <button
            className="px-3 py-1.5 rounded-full text-sm font-medium border border-success/30 bg-success-muted text-success hover:border-success/50 transition-all"
            onClick={() => setAmount(earnedRub)}
          >
            Всё ({formatCurrency(earnedRub)})
          </button>
        </div>

        <input
          className="w-full px-4 py-2.5 bg-harbor-elevated border border-border rounded-md text-text-primary placeholder:text-text-tertiary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/30 text-sm"
          type="number"
          placeholder="Введите сумму"
          value={amount === 0 ? '' : String(amount)}
          onChange={(e) => setAmount(parseFloat(e.target.value) || 0)}
        />

        {amount > 0 && (
          <div className="mt-3 space-y-1 text-sm">
            <div className="flex justify-between">
              <span className="text-text-secondary">Запрашиваемая сумма</span>
              <span className="font-mono text-text-primary">{formatCurrency(amount)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-secondary">Комиссия (1,5%)</span>
              <span className="font-mono text-danger">−{formatCurrency(fee)}</span>
            </div>
            <div className="flex justify-between pt-2 border-t border-border font-semibold">
              <span className="text-text-primary">Будет переведено</span>
              <span className="font-mono text-success">{formatCurrency(netAmount)}</span>
            </div>
          </div>
        )}

        {amount > 0 && amount < MIN_WITHDRAWAL && (
          <p className="text-xs text-danger mt-2">Минимальная сумма: {MIN_WITHDRAWAL.toLocaleString('ru-RU')} ₽</p>
        )}
        {amount > earnedRub && (
          <p className="text-xs text-danger mt-2">Сумма превышает доступный баланс</p>
        )}
      </Card>

      {/* Payment details */}
      <Card title="Реквизиты">
        <input
          className="w-full px-4 py-2.5 bg-harbor-elevated border border-border rounded-md text-text-primary placeholder:text-text-tertiary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/30 text-sm"
          type="text"
          placeholder="Номер карты или телефон для СБП"
          value={paymentDetails}
          onChange={(e) => setPaymentDetails(e.target.value)}
        />
      </Card>

      <Notification type="info">
        <span className="text-sm">⏱ Обработка: до 24 часов · 09:00–22:00 МСК</span>
      </Notification>

      <Button
        variant="primary"
        fullWidth
        loading={isPending}
        disabled={!isValid || isPending}
        onClick={handleSubmit}
      >
        {isPending ? '⏳ Отправка...' : '💸 Запросить вывод'}
      </Button>

      <Button variant="secondary" fullWidth onClick={() => navigate('/own/payouts')}>
        ← К выплатам
      </Button>
    </div>
  )
}
