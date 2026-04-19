import { useEffect, useMemo } from 'react'
import { useNavigate, useLocation, useSearchParams } from 'react-router-dom'
import { StepIndicator, FeeBreakdown, Notification, Button } from '@shared/ui'
import { formatCurrency } from '@/lib/constants'
import { useTopupStatus } from '@/hooks/useBillingQueries'

interface TopUpConfirmState {
  amount?: number
  paymentUrl?: string
  paymentId?: string
}

export default function TopUpConfirm() {
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams] = useSearchParams()
  const state = (location.state as TopUpConfirmState | null) ?? {}
  const { amount, paymentUrl } = state
  const paymentId = state.paymentId ?? searchParams.get('payment_id') ?? null

  useEffect(() => {
    if (!amount) navigate('/topup')
  }, [amount, navigate])

  const { status, timedOut } = useTopupStatus(paymentId)

  const statusView = useMemo(() => {
    if (status === 'succeeded') {
      return {
        type: 'success' as const,
        text: '✅ Оплата подтверждена — средства зачислены на баланс.',
      }
    }
    if (status === 'canceled') {
      return {
        type: 'danger' as const,
        text: '❌ Платёж отменён или не прошёл. Попробуйте ещё раз.',
      }
    }
    if (timedOut) {
      return {
        type: 'warning' as const,
        text: '⏳ Статус пока не получен — проверьте раздел «История операций» позже.',
      }
    }
    return {
      type: 'info' as const,
      text: '💳 Ожидаем подтверждение от ЮKassa — обычно 5–30 секунд.',
    }
  }, [status, timedOut])

  if (!amount) return null

  const fee = amount * 0.035
  const total = amount + fee

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-display font-bold text-text-primary">Подтверждение пополнения</h1>

      <StepIndicator total={2} current={2} labels={['Шаг 1 — Сумма', 'Шаг 2 — Подтверждение']} />

      <FeeBreakdown
        rows={[
          { label: 'Будет зачислено', value: formatCurrency(amount) },
          { label: 'Комиссия ЮKassa (3,5%)', value: `+${formatCurrency(fee)}` },
        ]}
        total={{ label: 'Итого к оплате', value: formatCurrency(total) }}
      />

      <Notification type={statusView.type}>
        <span className="text-sm">{statusView.text}</span>
      </Notification>

      <div className="space-y-3">
        {status === 'succeeded' ? (
          <>
            <Button variant="primary" fullWidth onClick={() => navigate('/cabinet')}>
              🏠 В кабинет
            </Button>
            <Button variant="secondary" fullWidth onClick={() => navigate('/billing/history')}>
              📜 История операций
            </Button>
          </>
        ) : (
          <>
            {paymentUrl && status !== 'canceled' && (
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
          </>
        )}
      </div>
    </div>
  )
}
