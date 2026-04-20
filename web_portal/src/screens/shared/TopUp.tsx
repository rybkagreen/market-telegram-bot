import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Notification, Button, Icon, StepIndicator, ScreenHeader, Toggle, Skeleton } from '@shared/ui'
import type { IconName } from '@shared/ui'
import { useMe } from '@/hooks/queries'
import { useInitiateTopup } from '@/hooks/useBillingQueries'

const CHIP_AMOUNTS = [500, 1000, 2000, 5000, 10000, 20000]
const FEE_RATE = 0.035
const MIN_AMOUNT = 500
const MAX_AMOUNT = 300_000

type PaymentMethod = 'card' | 'sbp' | 'wallet'

interface MethodRow {
  id: PaymentMethod
  icon: IconName
  name: string
  detail: string
}

const METHODS: MethodRow[] = [
  { id: 'card', icon: 'card', name: 'Банковская карта', detail: 'Visa, Mastercard, МИР · комиссия 3,5%' },
  { id: 'sbp', icon: 'zap', name: 'СБП', detail: 'По QR или номеру · комиссия 3,5%' },
  { id: 'wallet', icon: 'wallet', name: 'ЮMoney / Кошелёк', detail: 'Комиссия 3,5%' },
]

function fmt(v: number) {
  return new Intl.NumberFormat('ru-RU').format(Math.round(v))
}

export default function TopUp() {
  const navigate = useNavigate()
  const { data: user, isLoading: userLoading } = useMe()
  const [amount, setAmount] = useState(2000)
  const [chipSelected, setChipSelected] = useState<number | null>(2000)
  const [method, setMethod] = useState<PaymentMethod>('card')
  const [auto, setAuto] = useState(false)
  const topup = useInitiateTopup()

  const handleChip = (v: number) => {
    setAmount(v)
    setChipSelected(v)
  }

  const handleInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const parsed = parseInt(e.target.value.replace(/\D/g, ''), 10)
    setAmount(Number.isNaN(parsed) ? 0 : parsed)
    setChipSelected(null)
  }

  const isValid = amount >= MIN_AMOUNT && amount <= MAX_AMOUNT
  const fee = Math.round(amount * FEE_RATE)
  const total = amount + fee
  const belowMin = amount > 0 && amount < MIN_AMOUNT
  const aboveMax = amount > MAX_AMOUNT
  const balanceRub = Number(user?.balance_rub ?? 0)

  const handleTopUp = () => {
    topup.mutate(amount, {
      onSuccess: (data) => {
        window.open(data.payment_url, '_blank')
        navigate(`/topup/confirm?payment_id=${data.payment_id}`, {
          state: { amount, paymentUrl: data.payment_url, paymentId: data.payment_id },
        })
      },
    })
  }

  return (
    <div
      className="max-w-[1120px] mx-auto grid gap-7 items-start"
      style={{ gridTemplateColumns: 'minmax(0, 1fr) 360px' }}
    >
      <div>
        <ScreenHeader
          title="Пополнение баланса"
          subtitle="Два шага. Оплата через ЮKassa, средства зачисляются автоматически."
        />

        <div className="mb-6">
          <StepIndicator total={2} current={1} labels={['Сумма', 'Подтверждение']} />
        </div>

        <Section title="Выберите сумму" subtitle={`От ${fmt(MIN_AMOUNT)} ₽ до ${fmt(MAX_AMOUNT)} ₽`}>
          <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
            {CHIP_AMOUNTS.map((v) => {
              const active = chipSelected === v
              return (
                <button
                  key={v}
                  onClick={() => handleChip(v)}
                  className={`pt-3.5 pb-3 px-2.5 rounded-[9px] border text-center font-display text-[14.5px] font-semibold tracking-[-0.01em] transition-all ${
                    active
                      ? 'border-accent bg-accent-muted text-accent ring-[3px] ring-accent/15'
                      : 'border-border bg-harbor-elevated text-text-primary hover:border-border-active'
                  }`}
                >
                  <div>{fmt(v)}</div>
                  <div
                    className={`text-[11px] font-body font-medium mt-0.5 ${
                      active ? 'text-accent' : 'text-text-tertiary'
                    }`}
                  >
                    ₽
                  </div>
                </button>
              )
            })}
          </div>
        </Section>

        <Section title="Или введите свою сумму" className="mt-[18px]">
          <div className="relative flex items-stretch">
            <span className="absolute left-4 top-1/2 -translate-y-1/2 text-text-tertiary">
              <Icon name="ruble" size={17} />
            </span>
            <input
              type="text"
              inputMode="numeric"
              value={amount ? fmt(amount) : ''}
              onChange={handleInput}
              placeholder="0"
              className={`flex-1 py-4 pl-11 pr-[110px] rounded-[10px] border bg-harbor-elevated text-text-primary font-display text-[22px] font-semibold tracking-[-0.01em] outline-none transition-colors ${
                belowMin || aboveMax ? 'border-danger' : 'border-border focus:border-accent'
              }`}
            />
            <span className="absolute right-4 top-1/2 -translate-y-1/2 text-text-tertiary text-[13px] pointer-events-none">
              рублей
            </span>
          </div>

          {(belowMin || aboveMax) && (
            <div className="mt-2.5 text-[12.5px] text-danger flex items-center gap-1.5">
              <Icon name="warning" size={13} />
              {belowMin ? `Минимум — ${fmt(MIN_AMOUNT)} ₽` : `Максимум — ${fmt(MAX_AMOUNT)} ₽`}
            </div>
          )}
        </Section>

        <Section title="Способ оплаты" subtitle="ЮKassa — безопасный приём платежей" className="mt-[18px]">
          <div className="flex flex-col gap-2">
            {METHODS.map((m) => (
              <MethodRowBtn
                key={m.id}
                active={method === m.id}
                onClick={() => setMethod(m.id)}
                icon={m.icon}
                name={m.name}
                detail={m.detail}
              />
            ))}
          </div>
        </Section>

        <Section className="mt-[18px]">
          <div className="flex items-center justify-between gap-5">
            <div className="flex gap-3 items-start">
              <span className="grid place-items-center w-8.5 h-8.5 w-[34px] h-[34px] rounded-lg bg-accent-2-muted text-accent-2 flex-shrink-0">
                <Icon name="refresh" size={16} />
              </span>
              <div>
                <div className="font-display text-sm font-semibold text-text-primary mb-0.5">
                  Автопополнение
                </div>
                <div className="text-[12.5px] text-text-secondary leading-relaxed">
                  Автоматически пополнять на эту сумму при балансе ниже 500&nbsp;₽
                </div>
              </div>
            </div>
            <Toggle checked={auto} onChange={setAuto} />
          </div>
        </Section>
      </div>

      <aside className="sticky top-5 flex flex-col gap-3.5">
        <div className="bg-harbor-card border border-border rounded-xl p-5">
          <div className="font-display text-[13px] font-semibold text-text-primary mb-3.5 tracking-[-0.005em]">
            Итог пополнения
          </div>

          <div className="flex flex-col gap-2.5">
            <SummaryRow label="Сумма" value={`${fmt(amount)} ₽`} strong />
            <SummaryRow label="Комиссия (3,5%)" value={`+ ${fmt(fee)} ₽`} muted />
          </div>

          <div className="mt-3.5 pt-3.5 border-t border-dashed border-border flex items-baseline justify-between gap-2.5">
            <span className="font-display text-[13px] font-semibold text-text-secondary flex-shrink-0">
              К оплате
            </span>
            <span className="font-display font-bold text-[22px] text-text-primary tracking-[-0.02em] whitespace-nowrap tabular-nums">
              {fmt(total)} ₽
            </span>
          </div>

          <div className="mt-[18px]">
            <Button
              variant="primary"
              fullWidth
              size="lg"
              loading={topup.isPending}
              disabled={!isValid}
              iconLeft="card"
              onClick={handleTopUp}
            >
              Перейти к оплате
            </Button>
          </div>

          <div className="mt-3 text-[11.5px] text-text-tertiary text-center leading-[1.5]">
            Нажимая «Перейти к оплате», вы соглашаетесь
            <br />с условиями сервиса и офертой
          </div>
        </div>

        <div className="bg-gradient-to-br from-harbor-card to-harbor-secondary border border-border rounded-xl p-[18px] flex items-center gap-3.5">
          <span className="grid place-items-center w-[42px] h-[42px] rounded-[10px] bg-accent-muted text-accent">
            <Icon name="wallet" size={20} />
          </span>
          <div className="flex-1 min-w-0">
            <div className="text-[11px] text-text-tertiary uppercase tracking-wider font-semibold">
              Текущий баланс
            </div>
            <div className="font-display text-[22px] font-bold text-text-primary tracking-[-0.02em] mt-0.5 tabular-nums">
              {userLoading ? <Skeleton className="h-6 w-24" /> : `${fmt(balanceRub)} ₽`}
            </div>
          </div>
        </div>

        <Notification type="info">
          Средства поступят автоматически после подтверждения платежа. Обычно 5–30&nbsp;секунд.
        </Notification>
      </aside>
    </div>
  )
}

function Section({
  title,
  subtitle,
  children,
  className = '',
}: {
  title?: string
  subtitle?: string
  children: React.ReactNode
  className?: string
}) {
  return (
    <section className={`bg-harbor-card border border-border rounded-xl p-5 ${className}`}>
      {(title || subtitle) && (
        <div className="mb-3.5">
          {title && (
            <div className="font-display text-[13.5px] font-semibold text-text-primary tracking-[-0.005em]">
              {title}
            </div>
          )}
          {subtitle && <div className="text-xs text-text-tertiary mt-[3px]">{subtitle}</div>}
        </div>
      )}
      {children}
    </section>
  )
}

function MethodRowBtn({
  active,
  onClick,
  icon,
  name,
  detail,
}: {
  active: boolean
  onClick: () => void
  icon: IconName
  name: string
  detail: string
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex items-center gap-3.5 px-3.5 py-3 rounded-[9px] border text-left w-full transition-all ${
        active
          ? 'border-accent bg-accent-muted'
          : 'border-border bg-harbor-elevated hover:border-border-active'
      }`}
    >
      <span
        className={`grid place-items-center w-[38px] h-[38px] rounded-lg ${
          active ? 'bg-accent/15 text-accent' : 'bg-harbor-card text-text-secondary'
        }`}
      >
        <Icon name={icon} size={17} />
      </span>
      <div className="flex-1 min-w-0">
        <div className="font-display text-[13.5px] font-semibold text-text-primary">{name}</div>
        <div className="text-xs text-text-tertiary mt-px">{detail}</div>
      </div>
      <span
        className={`w-[18px] h-[18px] rounded-full border-2 grid place-items-center flex-shrink-0 ${
          active ? 'border-accent' : 'border-border-active'
        }`}
      >
        {active && <span className="w-2 h-2 rounded-full bg-accent" />}
      </span>
    </button>
  )
}

function SummaryRow({ label, value, strong, muted }: { label: string; value: string; strong?: boolean; muted?: boolean }) {
  return (
    <div className="flex justify-between items-baseline">
      <span className="text-[13px] text-text-secondary">{label}</span>
      <span
        className={`font-mono tabular-nums text-[13.5px] ${muted ? 'text-text-secondary' : 'text-text-primary'} ${strong ? 'font-semibold' : 'font-medium'}`}
      >
        {value}
      </span>
    </div>
  )
}
