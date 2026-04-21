import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Icon, Sparkline } from '@shared/ui'
import { formatCurrency } from '@/lib/constants'
import { useMe } from '@/hooks/queries'
import { useFrozenBalance, useTransactionHistory } from '@/hooks/useBillingQueries'

type Period = '7д' | '30д'

interface BalanceTileProps {
  tone: 'info' | 'success'
  label: string
  amount: string
  delta: string
  deltaDirection: 'up' | 'down' | 'neutral'
  spark: number[]
  period: Period
  onPeriodChange: (p: Period) => void
  secondary: { label: string; value: string }[]
  cta: { label: string; onClick?: () => void; disabled?: boolean }
}

function BalanceTile({
  tone,
  label,
  amount,
  delta,
  deltaDirection,
  spark,
  period,
  onPeriodChange,
  secondary,
  cta,
}: BalanceTileProps) {
  const toneColor = tone === 'success' ? 'oklch(0.72 0.18 160)' : 'oklch(0.70 0.16 230)'
  const deltaIsPositive = deltaDirection === 'up'
  const deltaClr = deltaIsPositive
    ? 'bg-success-muted text-success'
    : deltaDirection === 'down'
      ? 'bg-danger-muted text-danger'
      : 'text-text-tertiary'

  return (
    <div className="relative rounded-xl bg-harbor-card border border-border p-5 overflow-hidden">
      {/* Top accent stripe */}
      <div
        className="absolute top-0 left-0 right-0 h-0.5"
        style={{ background: `linear-gradient(90deg, ${toneColor}, transparent)` }}
      />

      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.08em] text-text-tertiary">
          <span
            className="inline-block w-1.5 h-1.5 rounded-full"
            style={{ background: toneColor, boxShadow: `0 0 8px ${toneColor}` }}
          />
          {label}
        </div>
        <div className="flex gap-0.5 p-0.5 rounded-md bg-harbor-secondary">
          {(['7д', '30д'] as Period[]).map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => onPeriodChange(p)}
              className={`px-2 py-0.5 text-[11px] font-semibold font-mono rounded transition-colors ${
                period === p
                  ? 'bg-harbor-elevated text-text-primary'
                  : 'text-text-tertiary hover:text-text-secondary'
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-3 flex items-baseline gap-2">
        <div
          className="font-display font-bold text-[40px] leading-none tabular-nums tracking-[-0.025em] text-text-primary"
        >
          {amount}
        </div>
        <div className="text-xl text-text-secondary font-medium">₽</div>
        {deltaDirection !== 'neutral' && (
          <div
            className={`ml-auto inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11.5px] font-mono font-semibold ${deltaClr}`}
          >
            <Icon name={deltaIsPositive ? 'arrow-up' : 'arrow-down'} size={11} />
            {delta}
          </div>
        )}
      </div>

      {deltaDirection === 'neutral' && (
        <div className="mt-1.5 flex items-center gap-1.5 text-xs text-text-tertiary">
          <Icon name="clock" size={12} />
          {delta}
        </div>
      )}

      <div className="mt-3 mb-4" style={{ color: toneColor }}>
        <Sparkline data={spark.length ? spark : [0, 0]} width={420} height={42} />
      </div>

      <div className="flex items-center gap-5 pt-3 border-t border-dashed border-border">
        {secondary.map((s) => (
          <div key={s.label}>
            <div className="text-[10.5px] uppercase tracking-[0.05em] text-text-tertiary font-medium">
              {s.label}
            </div>
            <div className="text-sm font-semibold text-text-primary font-mono tabular-nums mt-1">
              {s.value}
            </div>
          </div>
        ))}
        <button
          type="button"
          onClick={cta.disabled ? undefined : cta.onClick}
          disabled={cta.disabled}
          className={`ml-auto inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-md text-[12.5px] font-semibold transition-colors ${
            cta.disabled
              ? 'bg-harbor-secondary text-text-tertiary cursor-not-allowed'
              : 'text-white cursor-pointer hover:brightness-110'
          }`}
          style={cta.disabled ? undefined : { background: toneColor }}
        >
          <Icon name={tone === 'success' ? 'arrow-right' : 'plus'} size={13} />
          {cta.label}
        </button>
      </div>
    </div>
  )
}

function computeTrend(spark: number[]): { delta: string; direction: 'up' | 'down' | 'neutral' } {
  if (spark.length < 2) return { delta: '—', direction: 'neutral' }
  const first = spark[0]
  const last = spark[spark.length - 1]
  if (first === 0) {
    return last > 0
      ? { delta: '+' + last.toFixed(0), direction: 'up' }
      : { delta: '0%', direction: 'neutral' }
  }
  const pct = ((last - first) / Math.abs(first)) * 100
  if (Math.abs(pct) < 0.1) return { delta: '0%', direction: 'neutral' }
  const sign = pct > 0 ? '+' : ''
  return {
    delta: `${sign}${pct.toFixed(1)}%`,
    direction: pct > 0 ? 'up' : 'down',
  }
}

function buildBalanceSpark(transactions: ReadonlyArray<{ amount: string; type: string; created_at: string }> | undefined, days: number): number[] {
  if (!transactions?.length) return Array(days).fill(0)
  const start = new Date()
  start.setHours(0, 0, 0, 0)
  start.setDate(start.getDate() - (days - 1))
  const buckets: number[] = Array(days).fill(0)
  for (const tx of transactions) {
    const when = new Date(tx.created_at)
    const diffDays = Math.floor((when.getTime() - start.getTime()) / (1000 * 60 * 60 * 24))
    if (diffDays < 0 || diffDays >= days) continue
    const val = parseFloat(tx.amount)
    if (!Number.isFinite(val)) continue
    buckets[diffDays] += val
  }
  // Running total so the line shows running balance
  let running = 0
  return buckets.map((v) => {
    running += v
    return running
  })
}

export function BalanceHero() {
  const [period, setPeriod] = useState<Period>('7д')
  const days = period === '7д' ? 7 : 30
  const { data: user } = useMe()
  const { data: frozen } = useFrozenBalance()
  const { data: history } = useTransactionHistory(1, 100)

  const balanceNum = user ? parseFloat(user.balance_rub) : 0
  const earnedNum = user ? parseFloat(user.earned_rub) : 0
  const frozenNum = frozen ? parseFloat(frozen.total_frozen) : 0
  const navigate = useNavigate()

  const historyItems = history?.items
  const balanceSpark = useMemo(
    () => buildBalanceSpark(historyItems, days).map((v) => balanceNum + v),
    [historyItems, days, balanceNum],
  )
  const earningsSpark = useMemo(() => {
    const daysAgo: number[] = Array(days).fill(0)
    if (!historyItems) return daysAgo
    const start = new Date()
    start.setHours(0, 0, 0, 0)
    start.setDate(start.getDate() - (days - 1))
    for (const tx of historyItems) {
      if (tx.type !== 'escrow_release' && tx.type !== 'refund_full') continue
      const when = new Date(tx.created_at)
      const diffDays = Math.floor((when.getTime() - start.getTime()) / (1000 * 60 * 60 * 24))
      if (diffDays < 0 || diffDays >= days) continue
      daysAgo[diffDays] += parseFloat(tx.amount)
    }
    return daysAgo
  }, [historyItems, days])

  const balanceTrend = computeTrend(balanceSpark)
  const earningsTrend = computeTrend(earningsSpark)

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <BalanceTile
        tone="info"
        label="Баланс рекламодателя"
        amount={formatCurrency(balanceNum).replace(/[^\d\s,.]/g, '').trim()}
        delta={balanceTrend.delta}
        deltaDirection={balanceTrend.direction}
        spark={balanceSpark}
        period={period}
        onPeriodChange={setPeriod}
        secondary={[
          { label: 'Заморожено', value: `${frozenNum.toFixed(0)} ₽` },
          { label: 'Кампаний', value: String(frozen?.escrow_count ?? 0) },
        ]}
        cta={{ label: 'Пополнить', onClick: () => navigate('/topup') }}
      />
      <BalanceTile
        tone="success"
        label="Заработок"
        amount={formatCurrency(earnedNum).replace(/[^\d\s,.]/g, '').trim()}
        delta={earningsTrend.direction === 'neutral' ? 'Первая выплата откроется после настройки' : earningsTrend.delta}
        deltaDirection={earnedNum === 0 ? 'neutral' : earningsTrend.direction}
        spark={earningsSpark}
        period={period}
        onPeriodChange={setPeriod}
        secondary={[
          { label: 'В ожидании', value: '0 ₽' },
          { label: 'Каналов', value: '—' },
        ]}
        cta={{ label: 'К выплате', disabled: earnedNum === 0, onClick: () => navigate('/own/payouts') }}
      />
    </div>
  )
}
