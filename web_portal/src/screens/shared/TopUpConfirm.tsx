import { useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { StepIndicator, FeeBreakdown, Notification, Button } from '@shared/ui'
import { formatCurrency } from '@/lib/constants'

interface TopUpConfirmState {
  amount?: number
  paymentUrl?: string
}

export default function TopUpConfirm() {
  const navigate = useNavigate()
  const location = useLocation()
  const state = (location.state as TopUpConfirmState | null) ?? {}
  const { amount, paymentUrl } = state

  useEffect(() => {
    if (!amount) navigate('/topup')
  }, [amount, navigate])

  if (!amount) return null

  const fee = amount * 0.035
  const total = amount + fee

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-display font-bold text-text-primary">Подтверждение пополнения</h1>

      <StepIndicator total={2} current={1} labels={['Шаг 1 — Сумма', 'Шаг 2 — Подтверждение']} />

      <FeeBreakdown
        rows={[
          { label: 'Будет зачислено', value: formatCurrency(amount) },
          { label: 'Комиссия ЮKassa (3,5%)', value: `+${formatCurrency(fee)}` },
        ]}
        total={{ label: 'Итого к оплате', value: formatCurrency(total) }}
      />

      <Notification type="info">
        <span className="text-sm">💳 Оплата через ЮKassa — карта или СБП. Окно оплаты открыто в новой вкладке.</span>
      </Notification>

      <div className="space-y-3">
        {paymentUrl && (
          <Button variant="primary" fullWidth onClick={() => window.open(paymentUrl, '_blank')}>
            ✅ Открыть страницу оплаты снова
          </Button>
        )}
        <Button variant="secondary" fullWidth onClick={() => navigate('/topup')}>
          🔙 Изменить сумму
        </Button>
        <Button variant="ghost" fullWidth onClick={() => navigate('/cabinet')}>
          🏠 В кабинет
        </Button>
      </div>
    </div>
  )
}
