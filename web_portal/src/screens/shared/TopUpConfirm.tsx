import { useEffect, useState } from 'react'
import { useNavigate, useLocation, useSearchParams } from 'react-router-dom'
import {
  Notification,
  Button,
  Icon,
  StepIndicator,
  ScreenHeader,
} from '@shared/ui'
import type { IconName } from '@shared/ui'
import { useMe } from '@/hooks/queries'
import { useTopupStatus } from '@/hooks/useBillingQueries'
import { YOOKASSA_FEE, formatRatePct } from '@/lib/constants'

interface TopUpConfirmState {
  amount?: number
  paymentUrl?: string
  paymentId?: string
}

type LiveStatus = 'pending' | 'succeeded' | 'canceled' | 'timeout'

interface StatusViewConf {
  tone: 'info' | 'success' | 'danger' | 'warning'
  icon: IconName
  chipText: string
  title: string
  text: string
}

function fmt(v: number) {
  return new Intl.NumberFormat('ru-RU').format(Math.round(v))
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

  const { status: apiStatus, timedOut } = useTopupStatus(paymentId)
  const { data: user } = useMe()
  const [elapsed, setElapsed] = useState(0)

  const live: LiveStatus = timedOut
    ? 'timeout'
    : apiStatus === 'succeeded'
      ? 'succeeded'
      : apiStatus === 'canceled'
        ? 'canceled'
        : 'pending'

  useEffect(() => {
    if (live !== 'pending') return
    const t = window.setInterval(() => setElapsed((e) => e + 1), 1000)
    return () => window.clearInterval(t)
  }, [live])

  if (!amount) return null

  const fee = Math.round(amount * YOOKASSA_FEE)
  const total = amount + fee
  const balanceRub = Number(user?.balance_rub ?? 0)

  const confs: Record<LiveStatus, StatusViewConf> = {
    pending: {
      tone: 'info',
      icon: 'clock',
      chipText: 'Ожидание',
      title: 'Ожидаем подтверждение ЮKassa',
      text: 'Обычно 5–30 секунд. Не закрывайте эту страницу.',
    },
    succeeded: {
      tone: 'success',
      icon: 'check',
      chipText: 'Оплачено',
      title: 'Средства зачислены',
      text: `${fmt(amount)} ₽ уже на вашем балансе. Квитанция отправлена на email.`,
    },
    canceled: {
      tone: 'danger',
      icon: 'warning',
      chipText: 'Отменён',
      title: 'Платёж не прошёл',
      text: 'Оплата отменена или отклонена банком. Попробуйте ещё раз или измените способ оплаты.',
    },
    timeout: {
      tone: 'warning',
      icon: 'clock',
      chipText: 'Задержка',
      title: 'Статус задерживается',
      text: 'ЮKassa ещё не прислала подтверждение. Проверьте «Историю операций» через несколько минут.',
    },
  }

  const conf = confs[live]

  const toneText: Record<StatusViewConf['tone'], string> = {
    info: 'text-info',
    success: 'text-success',
    danger: 'text-danger',
    warning: 'text-warning',
  }
  const toneBg: Record<StatusViewConf['tone'], string> = {
    info: 'bg-info-muted',
    success: 'bg-success-muted',
    danger: 'bg-danger-muted',
    warning: 'bg-warning-muted',
  }
  const toneStripe: Record<StatusViewConf['tone'], string> = {
    info: 'from-info to-info/60',
    success: 'from-success to-success/60',
    danger: 'from-danger to-danger/60',
    warning: 'from-warning to-warning/60',
  }

  return (
    <div className="max-w-[820px] mx-auto">
      <ScreenHeader
        title="Подтверждение пополнения"
      />

      <div className="mb-7">
        <StepIndicator total={2} current={2} labels={['Сумма', 'Подтверждение']} />
      </div>

      <div className="bg-harbor-card border border-border rounded-2xl overflow-hidden mb-[18px]">
        <div className={`h-[3px] bg-gradient-to-r ${toneStripe[conf.tone]}`} />

        <div className="pt-7 px-7 pb-6">
          <div className="flex items-start gap-[18px]">
            <StatusGlyph status={live} icon={conf.icon} tone={conf.tone} />

            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2.5 mb-1.5 flex-wrap">
                <span
                  className={`text-[10px] font-bold tracking-[0.09em] uppercase px-2 py-1 rounded ${toneBg[conf.tone]} ${toneText[conf.tone]}`}
                >
                  {conf.chipText}
                </span>
                {paymentId && (
                  <span className="text-xs text-text-tertiary font-mono">
                    ID платежа: {paymentId.slice(0, 10)}
                  </span>
                )}
              </div>

              <div className="font-display text-[22px] font-bold text-text-primary tracking-[-0.02em] mb-1.5">
                {conf.title}
              </div>
              <div className="text-[13.5px] text-text-secondary leading-[1.55]">{conf.text}</div>

              {live === 'pending' && (
                <div className="mt-4 flex items-center gap-2.5">
                  <div className="flex-1 h-1 rounded-sm bg-harbor-elevated overflow-hidden relative">
                    <div
                      className="absolute inset-0 bg-gradient-to-r from-transparent via-accent to-transparent w-[40%]"
                      style={{ animation: 'indet 1.4s ease-in-out infinite' }}
                    />
                  </div>
                  <span className="font-mono text-xs text-text-tertiary tabular-nums min-w-[40px] text-right">
                    {elapsed}с
                  </span>
                </div>
              )}

              {live === 'succeeded' && (
                <div className="mt-4 py-2.5 px-3.5 bg-success-muted rounded-lg flex items-center gap-2.5">
                  <Icon name="wallet" size={16} className="text-success" />
                  <div className="text-[12.5px] text-text-primary">
                    Новый баланс:{' '}
                    <span className="font-mono font-semibold text-text-primary">
                      {fmt(balanceRub)} ₽
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="border-t border-border bg-harbor-secondary pt-[18px] pb-[18px] px-7">
          <div className="font-display text-xs font-semibold text-text-tertiary uppercase tracking-wider mb-3">
            Детали операции
          </div>
          <div className="flex flex-col gap-[9px]">
            <BreakdownRow label="Будет зачислено" value={`${fmt(amount)} ₽`} />
            <BreakdownRow label={`Комиссия ЮKassa (${formatRatePct(YOOKASSA_FEE)})`} value={`+ ${fmt(fee)} ₽`} muted />
          </div>
          <div className="mt-3 pt-3 border-t border-dashed border-border flex justify-between items-baseline gap-4">
            <span className="font-display text-sm font-semibold text-text-primary whitespace-nowrap">
              Итого оплачено
            </span>
            <span className="font-display font-bold text-xl text-text-primary tracking-[-0.02em] whitespace-nowrap tabular-nums">
              {fmt(total)} ₽
            </span>
          </div>
        </div>
      </div>

      <div
        className={`grid gap-2.5 grid-cols-1 ${live === 'succeeded' ? 'sm:grid-cols-2' : 'sm:grid-cols-3'}`}
      >
        {live === 'succeeded' ? (
          <>
            <Button variant="primary" fullWidth iconLeft="cabinet" onClick={() => navigate('/cabinet')}>
              В кабинет
            </Button>
            <Button
              variant="secondary"
              fullWidth
              iconLeft="receipt"
              onClick={() => navigate('/billing/history')}
            >
              История операций
            </Button>
          </>
        ) : live === 'canceled' ? (
          <>
            <Button variant="primary" fullWidth iconLeft="refresh" onClick={() => navigate('/topup')}>
              Попробовать снова
            </Button>
            <Button variant="secondary" fullWidth iconLeft="topup" onClick={() => navigate('/topup')}>
              Изменить сумму
            </Button>
            <Button variant="ghost" fullWidth iconLeft="cabinet" onClick={() => navigate('/cabinet')}>
              В кабинет
            </Button>
          </>
        ) : (
          <>
            {paymentUrl ? (
              <Button
                variant="primary"
                fullWidth
                iconLeft="external"
                onClick={() => window.open(paymentUrl, '_blank')}
              >
                Открыть страницу оплаты
              </Button>
            ) : (
              <Button variant="primary" fullWidth iconLeft="refresh" onClick={() => navigate('/topup')}>
                Повторить
              </Button>
            )}
            <Button variant="secondary" fullWidth iconLeft="topup" onClick={() => navigate('/topup')}>
              Изменить сумму
            </Button>
            <Button variant="ghost" fullWidth iconLeft="cabinet" onClick={() => navigate('/cabinet')}>
              В кабинет
            </Button>
          </>
        )}
      </div>

      <div className="mt-[18px]">
        <Notification type={live === 'succeeded' ? 'success' : 'info'}>
          {live === 'succeeded'
            ? 'Квитанция об операции отправлена на email. Она также доступна в разделе «Документы».'
            : 'Если что-то пошло не так — напишите в поддержку, мы быстро ответим.'}
        </Notification>
      </div>

      <style>{`
        @keyframes indet {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(250%); }
        }
        @keyframes pulse-ring {
          0% { transform: scale(0.8); opacity: 1; }
          100% { transform: scale(1.8); opacity: 0; }
        }
      `}</style>
    </div>
  )
}

function StatusGlyph({
  status,
  icon,
  tone,
}: {
  status: LiveStatus
  icon: IconName
  tone: StatusViewConf['tone']
}) {
  const toneBg: Record<StatusViewConf['tone'], string> = {
    info: 'bg-info-muted border-info/35 text-info',
    success: 'bg-success-muted border-success/35 text-success',
    danger: 'bg-danger-muted border-danger/35 text-danger',
    warning: 'bg-warning-muted border-warning/35 text-warning',
  }
  const toneRing: Record<StatusViewConf['tone'], string> = {
    info: 'border-info',
    success: 'border-success',
    danger: 'border-danger',
    warning: 'border-warning',
  }
  return (
    <div
      className={`relative w-14 h-14 rounded-[14px] border grid place-items-center flex-shrink-0 ${toneBg[tone]}`}
    >
      {status === 'pending' && (
        <span
          className={`absolute -inset-[2px] rounded-[14px] border-2 opacity-40 ${toneRing[tone]}`}
          style={{ animation: 'pulse-ring 1.6s ease-out infinite' }}
        />
      )}
      <Icon name={icon} size={24} strokeWidth={status === 'succeeded' ? 2.5 : 2} />
    </div>
  )
}

function BreakdownRow({ label, value, muted }: { label: string; value: string; muted?: boolean }) {
  return (
    <div className="flex justify-between items-baseline text-[13px] gap-4">
      <span className="text-text-secondary whitespace-nowrap">{label}</span>
      <span
        className={`font-mono tabular-nums whitespace-nowrap text-right ${muted ? 'text-text-secondary font-medium' : 'text-text-primary font-semibold'}`}
      >
        {value}
      </span>
    </div>
  )
}
