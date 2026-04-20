import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Button,
  Notification,
  Icon,
  ScreenHeader,
  FeeBreakdown,
} from '@shared/ui'
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

  const isValid = amount >= MIN_WITHDRAWAL && amount <= earnedRub && paymentDetails.length >= 5

  const handleSubmit = () => {
    createPayout(
      { amount, payment_details: paymentDetails },
      { onSuccess: () => navigate('/own/payouts') },
    )
  }

  return (
    <div className="max-w-[900px] mx-auto">
      <ScreenHeader
        title="Запросить вывод средств"
        subtitle="Комиссия 1,5% · минимум 1 000 ₽ · обработка до 24 часов"
        action={
          <Button
            variant="secondary"
            iconLeft="arrow-left"
            onClick={() => navigate('/own/payouts')}
          >
            К выплатам
          </Button>
        }
      />

      <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
        <div className="space-y-4">
          <div className="bg-harbor-card border border-border rounded-xl p-5">
            <div className="flex items-center gap-2 mb-3">
              <Icon name="wallet" size={14} className="text-text-tertiary" />
              <span className="font-display text-[14px] font-semibold text-text-primary">
                Сумма вывода
              </span>
            </div>

            <div className="flex gap-2 flex-wrap mb-3">
              {PRESET_AMOUNTS.map((a) => {
                const on = amount === a
                return (
                  <button
                    key={a}
                    className={`px-3 py-1.5 rounded-2xl text-xs font-semibold border transition-all ${
                      on
                        ? 'border-accent bg-accent-muted text-accent'
                        : 'border-border bg-transparent text-text-secondary hover:border-border-active'
                    }`}
                    onClick={() => setAmount(a)}
                  >
                    {a.toLocaleString('ru-RU')} ₽
                  </button>
                )
              })}
              <button
                className="px-3 py-1.5 rounded-2xl text-xs font-semibold border border-success/35 bg-success-muted text-success hover:brightness-110 transition-all"
                onClick={() => setAmount(earnedRub)}
              >
                Всё — {formatCurrency(earnedRub)}
              </button>
            </div>

            <input
              className="w-full px-4 py-3 bg-harbor-elevated border border-border rounded-lg text-text-primary font-mono tabular-nums font-bold text-[20px] focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/25"
              type="number"
              placeholder="0"
              value={amount === 0 ? '' : String(amount)}
              onChange={(e) => setAmount(parseFloat(e.target.value) || 0)}
            />

            {amount > 0 && amount < MIN_WITHDRAWAL && (
              <p className="text-[12px] text-danger mt-2 flex items-center gap-1.5">
                <Icon name="warning" size={12} />
                Минимальная сумма: {MIN_WITHDRAWAL.toLocaleString('ru-RU')} ₽
              </p>
            )}
            {amount > earnedRub && (
              <p className="text-[12px] text-danger mt-2 flex items-center gap-1.5">
                <Icon name="warning" size={12} />
                Сумма превышает доступный баланс
              </p>
            )}
          </div>

          <div className="bg-harbor-card border border-border rounded-xl p-5">
            <div className="flex items-center gap-2 mb-3">
              <Icon name="bank" size={14} className="text-text-tertiary" />
              <span className="font-display text-[14px] font-semibold text-text-primary">
                Реквизиты
              </span>
            </div>
            <input
              className="w-full px-4 py-3 bg-harbor-elevated border border-border rounded-lg text-text-primary placeholder:text-text-tertiary focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/25 text-sm font-mono tabular-nums"
              type="text"
              placeholder="Номер карты или телефон для СБП"
              value={paymentDetails}
              onChange={(e) => setPaymentDetails(e.target.value)}
            />
            <p className="text-[11.5px] text-text-tertiary mt-2 flex items-center gap-1.5">
              <Icon name="info" size={12} />
              Укажите реквизиты банка, куда перечислить средства.
            </p>
          </div>

          <Notification type="info">
            Обработка занимает до 24 часов. Выплаты совершаются в рабочие часы банка (09:00–22:00 МСК).
          </Notification>
        </div>

        <div className="space-y-4">
          <div className="bg-harbor-card border border-border rounded-xl p-5 h-fit">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-text-tertiary mb-1">
              Доступно
            </div>
            <div className="font-display text-[28px] font-bold tracking-[-0.02em] text-success tabular-nums">
              {formatCurrency(earnedRub)}
            </div>
          </div>

          <div className="bg-harbor-card border border-border rounded-xl p-5">
            <div className="font-display text-[14px] font-semibold text-text-primary mb-3">
              Расчёт
            </div>
            {amount > 0 ? (
              <FeeBreakdown
                rows={[
                  { label: 'Запрос', value: formatCurrency(amount) },
                  { label: 'Комиссия 1,5%', value: `−${formatCurrency(fee)}` },
                ]}
                total={{ label: 'К зачислению', value: formatCurrency(netAmount) }}
              />
            ) : (
              <p className="text-[12.5px] text-text-tertiary">
                Выберите сумму — покажем комиссию и итог.
              </p>
            )}
          </div>

          <Button
            variant="primary"
            fullWidth
            iconLeft="payouts"
            loading={isPending}
            disabled={!isValid || isPending}
            onClick={handleSubmit}
          >
            Запросить вывод
          </Button>
        </div>
      </div>
    </div>
  )
}
