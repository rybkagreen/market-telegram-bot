import { memo, useMemo, useState } from 'react'
import { useCashflow } from '@/hooks/useAnalyticsQueries'
import type { CashflowDays } from '@/api/analytics'

function formatRub(value: number): string {
  const abs = Math.abs(value)
  const formatted = abs.toLocaleString('ru-RU', { maximumFractionDigits: 0 })
  return `${value < 0 ? '−' : ''}${formatted} ₽`
}

function PerformanceChartInner() {
  const [days, setDays] = useState<CashflowDays>(30)
  const { data, isLoading, isError } = useCashflow(days)

  const { income, expense, maxVal, gridLines, xTicks } = useMemo(() => {
    const points = data?.points ?? []
    const incomeArr = points.map((p) => parseFloat(p.income) || 0)
    const expenseArr = points.map((p) => parseFloat(p.expense) || 0)
    const maxRaw = Math.max(...incomeArr, ...expenseArr, 0)
    const max = (maxRaw === 0 ? 500 : maxRaw) * 1.2
    const grid = [0, 0.25, 0.5, 0.75, 1].map((r) => ({
      r,
      v: Math.round((max * (1 - r)) / 50) * 50,
    }))
    const ticks =
      days === 7
        ? [0, 2, 4, 6]
        : days === 30
          ? [0, 7, 14, 21, 29]
          : [0, 30, 60, 89]
    return { income: incomeArr, expense: expenseArr, maxVal: max, gridLines: grid, xTicks: ticks }
  }, [data?.points, days])

  const W = 600
  const H = 200
  const padL = 36
  const padR = 8
  const padT = 16
  const padB = 26

  const n = Math.max(income.length, 1)
  const stepX = n > 1 ? (W - padL - padR) / (n - 1) : 0
  const mapX = (i: number) => padL + i * stepX
  const mapY = (v: number) => padT + (H - padT - padB) * (1 - v / maxVal)

  const line = (arr: number[]): string =>
    arr.length === 0
      ? ''
      : arr.map((v, i) => (i ? 'L' : 'M') + mapX(i).toFixed(1) + ' ' + mapY(v).toFixed(1)).join(' ')
  const area = (arr: number[]): string =>
    arr.length === 0
      ? ''
      : `${line(arr)} L ${mapX(arr.length - 1).toFixed(1)} ${H - padB} L ${padL} ${H - padB} Z`

  const totalIncome = data ? parseFloat(data.total_income) : 0
  const totalExpense = data ? parseFloat(data.total_expense) : 0
  const net = data ? parseFloat(data.net) : 0

  return (
    <section className="rounded-xl bg-harbor-card border border-border overflow-hidden">
      <header className="flex items-center justify-between px-5 py-4 border-b border-border">
        <div>
          <h3 className="font-display text-[15px] font-semibold text-text-primary">
            Финансовая активность
          </h3>
          <p className="text-xs text-text-tertiary mt-0.5">Доходы и расходы за период</p>
        </div>
        <div className="flex gap-0.5 p-0.5 rounded-md bg-harbor-secondary border border-border">
          {([7, 30, 90] as CashflowDays[]).map((d) => (
            <button
              key={d}
              type="button"
              onClick={() => setDays(d)}
              className={`px-2.5 py-0.5 text-[11px] font-semibold font-mono rounded transition-colors ${
                days === d
                  ? 'bg-harbor-elevated text-text-primary'
                  : 'text-text-tertiary hover:text-text-secondary'
              }`}
            >
              {d}д
            </button>
          ))}
        </div>
      </header>

      <div className="px-5 pt-4">
        <div className="flex items-start gap-6 mb-3">
          <div>
            <div className="text-[10.5px] uppercase tracking-[0.06em] text-text-tertiary flex items-center gap-1.5">
              <span className="inline-block w-2 h-0.5 rounded bg-success" />
              Доходы
            </div>
            <div className="font-display text-xl font-bold text-text-primary tabular-nums mt-1">
              {formatRub(totalIncome)}
            </div>
          </div>
          <div>
            <div className="text-[10.5px] uppercase tracking-[0.06em] text-text-tertiary flex items-center gap-1.5">
              <span className="inline-block w-2 h-0.5 rounded bg-danger" />
              Расходы
            </div>
            <div className="font-display text-xl font-bold text-text-primary tabular-nums mt-1">
              {formatRub(totalExpense)}
            </div>
          </div>
          <div className="ml-auto text-right">
            <div className="text-[10.5px] uppercase tracking-[0.06em] text-text-tertiary">Нетто</div>
            <div
              className={`font-display text-xl font-bold tabular-nums mt-1 ${
                net >= 0 ? 'text-success' : 'text-danger'
              }`}
            >
              {formatRub(net)}
            </div>
          </div>
        </div>
      </div>

      <div className="px-3 pb-4">
        {isLoading ? (
          <div className="h-[200px] flex items-center justify-center text-sm text-text-tertiary">
            Загрузка…
          </div>
        ) : isError ? (
          <div className="h-[200px] flex items-center justify-center text-sm text-danger">
            Ошибка загрузки данных
          </div>
        ) : (
          <svg viewBox={`0 0 ${W} ${H}`} className="w-full block" preserveAspectRatio="none">
            <defs>
              <linearGradient id="cashflow_income_grad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="oklch(0.72 0.18 160)" stopOpacity="0.25" />
                <stop offset="100%" stopColor="oklch(0.72 0.18 160)" stopOpacity="0" />
              </linearGradient>
              <linearGradient id="cashflow_expense_grad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="oklch(0.65 0.22 25)" stopOpacity="0.2" />
                <stop offset="100%" stopColor="oklch(0.65 0.22 25)" stopOpacity="0" />
              </linearGradient>
            </defs>

            {gridLines.map((g, i) => {
              const y = padT + (H - padT - padB) * g.r
              return (
                <g key={i}>
                  <line
                    x1={padL}
                    x2={W - padR}
                    y1={y}
                    y2={y}
                    stroke="oklch(1 0 0 / 0.06)"
                    strokeDasharray="2 3"
                  />
                  <text
                    x={padL - 6}
                    y={y + 3}
                    fontSize="9"
                    fill="oklch(0.40 0.05 260)"
                    textAnchor="end"
                    fontFamily="JetBrains Mono, monospace"
                  >
                    {g.v}
                  </text>
                </g>
              )
            })}

            {xTicks.map((i) => (
              <text
                key={i}
                x={mapX(i)}
                y={H - padB + 14}
                fontSize="9"
                fill="oklch(0.40 0.05 260)"
                textAnchor="middle"
                fontFamily="JetBrains Mono, monospace"
              >
                {i === 0 ? `${days}д` : i === n - 1 ? 'сейчас' : `${days - i}д`}
              </text>
            ))}

            {income.length > 0 && (
              <>
                <path d={area(expense)} fill="url(#cashflow_expense_grad)" />
                <path d={area(income)} fill="url(#cashflow_income_grad)" />
                <path
                  d={line(expense)}
                  stroke="oklch(0.65 0.22 25)"
                  strokeWidth="1.8"
                  fill="none"
                  strokeLinejoin="round"
                />
                <path
                  d={line(income)}
                  stroke="oklch(0.72 0.18 160)"
                  strokeWidth="1.8"
                  fill="none"
                  strokeLinejoin="round"
                />
                <circle cx={mapX(n - 1)} cy={mapY(income[n - 1] || 0)} r="3" fill="oklch(0.72 0.18 160)" />
                <circle cx={mapX(n - 1)} cy={mapY(expense[n - 1] || 0)} r="3" fill="oklch(0.65 0.22 25)" />
              </>
            )}
          </svg>
        )}
      </div>
    </section>
  )
}

export const PerformanceChart = memo(PerformanceChartInner)
