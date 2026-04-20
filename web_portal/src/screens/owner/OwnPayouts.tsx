import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Button,
  EmptyState,
  Skeleton,
  Icon,
  ScreenHeader,
} from '@shared/ui'
import type { IconName } from '@shared/ui'
import { formatCurrency, formatDateTimeMSK } from '@/lib/constants'
import { useMe } from '@/hooks/queries'
import { useMyPayouts } from '@/hooks/usePayoutQueries'

const COOLDOWN_HOURS = 24

type Tone = 'success' | 'warning' | 'danger' | 'neutral'

const PAYOUT_STATUS_META: Record<string, { label: string; tone: Tone; icon: IconName }> = {
  paid: { label: 'Выплачено', tone: 'success', icon: 'check' },
  processing: { label: 'В обработке', tone: 'warning', icon: 'hourglass' },
  pending: { label: 'Ожидает', tone: 'warning', icon: 'clock' },
  rejected: { label: 'Отклонено', tone: 'danger', icon: 'close' },
  cancelled: { label: 'Отменено', tone: 'neutral', icon: 'close' },
}

const toneClasses: Record<Tone, string> = {
  success: 'bg-success-muted text-success',
  warning: 'bg-warning-muted text-warning',
  danger: 'bg-danger-muted text-danger',
  neutral: 'bg-harbor-elevated text-text-tertiary',
}

function formatCountdown(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000)
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

export default function OwnPayouts() {
  const navigate = useNavigate()
  const { data: me } = useMe()
  const { data: payouts = [], isLoading, refetch } = useMyPayouts()
  const [cooldownRemaining, setCooldownRemaining] = useState(0)

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (payouts.length === 0) return
    const lastPayout = payouts.reduce(
      (latest, p) => (new Date(p.created_at) > new Date(latest.created_at) ? p : latest),
      payouts[0],
    )
    const cooldownEnd = new Date(lastPayout.created_at).getTime() + COOLDOWN_HOURS * 3600 * 1000
    const remaining = cooldownEnd - Date.now()

    if (remaining > 0) {
      setCooldownRemaining(remaining)
      const timer = setInterval(() => {
        setCooldownRemaining((prev) => {
          const next = prev - 1000
          return next > 0 ? next : 0
        })
      }, 1000)
      return () => clearInterval(timer)
    } else {
      setCooldownRemaining(0)
    }
  }, [payouts])
  /* eslint-enable react-hooks/set-state-in-effect */

  const earnedRub = Number(me?.earned_rub ?? '0')
  const isCooldownActive = cooldownRemaining > 0

  const totalPaid = payouts
    .filter((p) => p.status === 'paid')
    .reduce((s, p) => s + parseFloat(String(p.net_amount)), 0)

  return (
    <div className="max-w-[1080px] mx-auto">
      <ScreenHeader
        crumbs={['Главная', 'Владелец', 'Выплаты']}
        title="Выплаты"
        subtitle="Доступные средства, лимиты и история выводов"
        action={
          <Button variant="secondary" iconLeft="refresh" onClick={() => void refetch()}>
            Обновить
          </Button>
        }
      />

      <div className="bg-harbor-card border border-border rounded-xl p-5 mb-5 relative overflow-hidden">
        <div className="absolute top-0 left-0 right-0 h-[3px] bg-gradient-to-r from-success to-accent" />
        <div className="flex items-start justify-between gap-5 flex-wrap">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-wider text-text-tertiary mb-1">
              Доступно к выводу
            </div>
            <div className="font-display text-[34px] font-bold tracking-[-0.02em] text-success tabular-nums">
              {formatCurrency(earnedRub)}
            </div>
            <div className="text-[12.5px] text-text-tertiary mt-1 flex items-center gap-2">
              <Icon name="info" size={12} />
              Минимум {formatCurrency(1000)} · комиссия 1,5% · кулдаун 24 ч
            </div>
            {isCooldownActive && (
              <div className="mt-2 text-[13px] text-warning flex items-center gap-1.5">
                <Icon name="clock" size={13} />
                Следующая выплата через{' '}
                <span className="font-mono tabular-nums font-semibold">
                  {formatCountdown(cooldownRemaining)}
                </span>
              </div>
            )}
          </div>
          <div className="flex flex-col sm:flex-row gap-2.5">
            <Button
              variant="primary"
              iconLeft="payouts"
              disabled={isCooldownActive}
              onClick={() => navigate('/own/payouts/request')}
            >
              {isCooldownActive ? 'Временно недоступно' : 'Запросить вывод'}
            </Button>
          </div>
        </div>
      </div>

      <div
        className="grid gap-3.5 mb-5"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}
      >
        <SummaryTile
          icon="check"
          tone="success"
          label="Выплачено всего"
          value={formatCurrency(totalPaid)}
          delta={`${payouts.filter((p) => p.status === 'paid').length} операций`}
        />
        <SummaryTile
          icon="hourglass"
          tone="warning"
          label="В обработке"
          value={String(payouts.filter((p) => p.status === 'processing' || p.status === 'pending').length)}
          delta="Переведены банку"
        />
        <SummaryTile
          icon="close"
          tone="neutral"
          label="Отклонено"
          value={String(payouts.filter((p) => p.status === 'rejected').length)}
          delta="Возврат на баланс"
        />
      </div>

      <div className="bg-harbor-card border border-border rounded-xl overflow-hidden">
        <div className="px-5 py-3 border-b border-border flex items-center gap-2">
          <Icon name="transaction" size={14} className="text-text-tertiary" />
          <span className="font-display text-[14px] font-semibold text-text-primary">
            История выплат
          </span>
        </div>

        {isLoading ? (
          <div className="p-5 space-y-3">
            <Skeleton className="h-16" />
            <Skeleton className="h-16" />
          </div>
        ) : payouts.length === 0 ? (
          <div className="p-6">
            <EmptyState icon="payouts" title="Пока нет выплат" description="Запросите первую выплату после публикации размещения." />
          </div>
        ) : (
          <div>
            {payouts.map((payout, i) => {
              const meta =
                PAYOUT_STATUS_META[payout.status] ??
                { label: payout.status, tone: 'neutral' as Tone, icon: 'info' as IconName }
              return (
                <div
                  key={payout.id}
                  className={`flex items-center gap-4 px-[18px] py-3.5 hover:bg-harbor-elevated/40 transition-colors ${i === payouts.length - 1 ? '' : 'border-b border-border'}`}
                >
                  <span
                    className={`grid place-items-center w-10 h-10 rounded-[10px] flex-shrink-0 ${toneClasses[meta.tone]}`}
                  >
                    <Icon name={meta.icon} size={16} />
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-baseline gap-2.5 flex-wrap">
                      <span className="text-[13.5px] font-semibold text-text-primary">
                        Выплата #{payout.id}
                      </span>
                      <span
                        className={`text-[10.5px] font-bold tracking-[0.08em] uppercase py-0.5 px-1.5 rounded ${toneClasses[meta.tone]}`}
                      >
                        {meta.label}
                      </span>
                    </div>
                    <div className="text-[11.5px] text-text-tertiary mt-0.5 tabular-nums">
                      {formatDateTimeMSK(payout.created_at)} МСК
                    </div>
                  </div>
                  <div className="text-right min-w-[160px]">
                    <div className="text-[11px] uppercase tracking-wider text-text-tertiary">
                      Запрошено
                    </div>
                    <div className="font-mono tabular-nums text-[13px] text-text-secondary">
                      {formatCurrency(payout.gross_amount)}
                    </div>
                  </div>
                  <div className="text-right min-w-[120px]">
                    <div className="text-[11px] uppercase tracking-wider text-text-tertiary">
                      К зачислению
                    </div>
                    <div className="font-mono tabular-nums font-semibold text-[14px] text-success">
                      {formatCurrency(payout.net_amount)}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

const toneIconBg: Record<'success' | 'warning' | 'neutral', string> = {
  success: 'bg-success-muted text-success',
  warning: 'bg-warning-muted text-warning',
  neutral: 'bg-harbor-elevated text-text-tertiary',
}

function SummaryTile({
  icon,
  tone,
  label,
  value,
  delta,
}: {
  icon: IconName
  tone: 'success' | 'warning' | 'neutral'
  label: string
  value: string
  delta: string
}) {
  return (
    <div className="bg-harbor-card border border-border rounded-xl p-[18px] flex gap-3.5 items-start">
      <span
        className={`grid place-items-center w-[42px] h-[42px] rounded-[10px] flex-shrink-0 ${toneIconBg[tone]}`}
      >
        <Icon name={icon} size={18} />
      </span>
      <div className="flex-1 min-w-0">
        <div className="text-[11px] font-semibold uppercase tracking-wider text-text-tertiary mb-1">
          {label}
        </div>
        <div className="font-display text-xl font-bold text-text-primary tracking-[-0.02em] tabular-nums truncate">
          {value}
        </div>
        <div className="text-[11.5px] text-text-tertiary mt-0.5 truncate">{delta}</div>
      </div>
    </div>
  )
}
