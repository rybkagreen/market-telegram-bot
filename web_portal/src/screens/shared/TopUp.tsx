import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Notification, Button } from '@shared/ui'
import { formatCurrency } from '@/lib/constants'
import { useInitiateTopup } from '@/hooks/useBillingQueries'

const CHIP_AMOUNTS = [500, 1000, 2000, 5000, 10000, 20000]

export default function TopUp() {
  const navigate = useNavigate()
  const [amount, setAmount] = useState(2000)
  const [chipSelected, setChipSelected] = useState<number | undefined>(2000)
  const topup = useInitiateTopup()

  const handleChipSelect = (value: number) => {
    setAmount(value)
    setChipSelected(value)
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const parsed = parseInt(e.target.value, 10)
    setAmount(isNaN(parsed) ? 0 : parsed)
    setChipSelected(undefined)
  }

  const isValid = amount >= 500 && amount <= 300_000
  const yookassaFee = (amount * 0.035).toFixed(0)
  const totalToPay = amount + parseInt(yookassaFee, 10)

  const handleTopUp = () => {
    topup.mutate(amount, {
      onSuccess: (data) => {
        // Redirect to YooKassa payment page
        window.open(data.payment_url, '_blank')
        navigate(`/topup/confirm?payment_id=${data.payment_id}`, {
          state: { amount, paymentUrl: data.payment_url },
        })
      },
    })
  }

  return (
    <div className="space-y-6 max-w-xl">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-display font-bold text-text-primary">Пополнение баланса</h1>
        <p className="text-text-secondary mt-1">Мин. 500 ₽ · Макс. 300 000 ₽</p>
      </div>

      {/* Amount chips */}
      <Card title="Выберите сумму">
        <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
          {CHIP_AMOUNTS.map((value) => (
            <button
              key={value}
              className={`py-3 rounded-md text-sm font-medium transition-colors ${
                chipSelected === value
                  ? 'bg-accent text-accent-text'
                  : 'bg-harbor-elevated text-text-secondary hover:bg-harbor-elevated hover:text-text-primary'
              }`}
              onClick={() => handleChipSelect(value)}
            >
              {value.toLocaleString('ru-RU')} ₽
            </button>
          ))}
        </div>
      </Card>

      {/* Custom input */}
      <Card>
        <label className="block text-sm text-text-secondary mb-2">Или введите свою сумму</label>
        <input
          type="number"
          className="w-full px-3 py-2 rounded-md border border-border-active bg-harbor-elevated text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent"
          placeholder="от 500 ₽"
          value={amount || ''}
          onChange={handleInputChange}
          min={500}
          max={300000}
        />
      </Card>

      {/* Fee breakdown */}
      {isValid && (
        <Card title="Детали пополнения">
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-text-secondary">Зачислить на баланс</span>
              <span className="font-mono text-text-primary">{formatCurrency(amount)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-secondary">Комиссия ЮKassa (3.5%)</span>
              <span className="font-mono text-text-secondary">{formatCurrency(yookassaFee)}</span>
            </div>
            <div className="border-t border-border pt-2 flex justify-between">
              <span className="font-semibold text-text-primary">К оплате</span>
              <span className="font-mono font-bold text-text-primary">{formatCurrency(totalToPay)}</span>
            </div>
          </div>
        </Card>
      )}

      {/* Action */}
      <Button
        variant="primary"
        fullWidth
        loading={topup.isPending}
        disabled={!isValid || topup.isPending}
        onClick={handleTopUp}
      >
        {topup.isPending ? '⏳ Создание платежа...' : '💳 Пополнить баланс'}
      </Button>

      <Notification type="info">
        Оплата через ЮKassa. Средства зачисляются автоматически после подтверждения платежа.
      </Notification>
    </div>
  )
}
