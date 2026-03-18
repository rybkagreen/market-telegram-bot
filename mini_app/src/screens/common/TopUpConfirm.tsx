import { useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { StepIndicator, FeeBreakdown, Notification, Button } from '@/components/ui'
import { formatCurrency, calcTopUpFee } from '@/lib/formatters'
import { useHaptic } from '@/hooks/useHaptic'
import { useCreateTopUp } from '@/hooks/queries'
import styles from './TopUpConfirm.module.css'

export default function TopUpConfirm() {
  const navigate = useNavigate()
  const location = useLocation()
  const haptic = useHaptic()
  const amount: number | undefined = (location.state as { amount?: number })?.amount
  const createTopUp = useCreateTopUp()

  useEffect(() => {
    if (!amount) navigate('/topup')
  }, [amount, navigate])

  if (!amount) return null

  const { desired, fee, total } = calcTopUpFee(amount)

  const handlePay = () => {
    haptic.success()
    createTopUp.mutate(desired, {
      onSuccess: (data) => {
        if (window.Telegram?.WebApp?.openLink) {
          window.Telegram.WebApp.openLink(data.payment_url)
        } else {
          window.open(data.payment_url, '_blank')
        }
      },
    })
  }

  return (
    <ScreenShell>
      <StepIndicator
        total={2}
        current={1}
        labels={['Шаг 1 — Укажите сумму пополнения', 'Шаг 2 — Подтверждение']}
      />

      <div className={styles.breakdown}>
        <FeeBreakdown
          rows={[
            { label: 'Будет зачислено', value: formatCurrency(desired) },
            { label: 'Комиссия ЮKassa (3,5%)', value: '+' + formatCurrency(fee), dim: true },
          ]}
          total={{ label: 'Итого к оплате', value: formatCurrency(total) }}
        />
      </div>

      <Notification type="info">💳 Оплата через ЮKassa — карта или СБП</Notification>

      <div className={styles.buttons}>
        <Button
          variant="primary"
          fullWidth
          onClick={handlePay}
          disabled={createTopUp.isPending}
        >
          {createTopUp.isPending ? '⏳ Создание платежа…' : '✅ Перейти к оплате'}
        </Button>
        <Button variant="secondary" fullWidth onClick={() => navigate('/topup')}>
          🔙 Изменить сумму
        </Button>
      </div>
    </ScreenShell>
  )
}
