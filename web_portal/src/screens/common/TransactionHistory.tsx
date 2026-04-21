import { useMemo, useState } from 'react'
import { Button, Skeleton, Notification, Icon, ScreenHeader } from '@shared/ui'
import type { IconName } from '@shared/ui'
import { useTransactionHistory } from '@/hooks/useBillingQueries'
import { useMe } from '@/hooks/queries'
import type { TransactionItem } from '@/api/billing'

type AccentKey = 'info' | 'success' | 'warning' | 'danger' | 'neutral'

interface TxMeta {
  label: string
  icon: IconName
  incoming: boolean
  accent: AccentKey
}

const TX_META: Record<string, TxMeta> = {
  topup: { label: 'Пополнение баланса', icon: 'topup', incoming: true, accent: 'info' },
  escrow_freeze: { label: 'Оплата эскроу', icon: 'lock', incoming: false, accent: 'warning' },
  escrow_release: { label: 'Получение выплаты', icon: 'check', incoming: true, accent: 'success' },
  payout: { label: 'Вывод средств', icon: 'payouts', incoming: false, accent: 'info' },
  payout_fee: { label: 'Комиссия за вывод', icon: 'docs', incoming: false, accent: 'neutral' },
  refund_full: { label: 'Возврат средств', icon: 'refresh', incoming: true, accent: 'success' },
  adjustment: { label: 'Корректировка', icon: 'zap', incoming: true, accent: 'neutral' },
}

const STATUS_LABEL: Record<string, string> = {
  completed: 'Выполнено',
  succeeded: 'Выполнено',
  pending: 'В обработке',
  canceled: 'Отменено',
  failed: 'Ошибка',
}

interface FilterConf {
  id: 'all' | 'income' | 'outcome' | 'topup' | 'escrow' | 'payout'
  label: string
}

const FILTERS: FilterConf[] = [
  { id: 'all', label: 'Все' },
  { id: 'income', label: 'Поступления' },
  { id: 'outcome', label: 'Списания' },
  { id: 'topup', label: 'Пополнения' },
  { id: 'escrow', label: 'Эскроу' },
  { id: 'payout', label: 'Выплаты' },
]

type PeriodId = '7' | '30' | '90' | 'all'

const PERIODS: { id: PeriodId; label: string }[] = [
  { id: '7', label: '7 дней' },
  { id: '30', label: '30 дней' },
  { id: '90', label: '90 дней' },
  { id: 'all', label: 'Всё время' },
]

function fmtRub(v: number) {
  return new Intl.NumberFormat('ru-RU').format(Math.round(v)) + ' ₽'
}

function fmtDateTime(iso: string) {
  const d = new Date(iso)
  return d
    .toLocaleString('ru-RU', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'Europe/Moscow',
    })
    .replace(',', ' ·')
}

function dayKey(iso: string) {
  const d = new Date(iso)
  return d.toLocaleDateString('ru-RU', {
    day: '2-digit',
    month: 'long',
    timeZone: 'Europe/Moscow',
  })
}

function getMeta(type: string): TxMeta {
  return TX_META[type] ?? { label: type, icon: 'docs', incoming: true, accent: 'neutral' }
}

function periodCutoffMs(period: PeriodId): number | null {
  if (period === 'all') return null
  return Date.now() - Number(period) * 24 * 3600 * 1000
}

export default function TransactionHistory() {
  const [page, setPage] = useState(1)
  const [filter, setFilter] = useState<FilterConf['id']>('all')
  const [period, setPeriod] = useState<PeriodId>('30')
  const [search, setSearch] = useState('')
  const { data, isLoading, isError, refetch } = useTransactionHistory(page, 30)
  const { data: user } = useMe()

  const filtered = useMemo(() => {
    if (!data) return []
    const cutoff = periodCutoffMs(period)
    return data.items.filter((tx) => {
      const meta = getMeta(tx.type)
      if (cutoff !== null && new Date(tx.created_at).getTime() < cutoff) return false
      if (filter === 'income' && !meta.incoming) return false
      if (filter === 'outcome' && meta.incoming) return false
      if (filter === 'topup' && tx.type !== 'topup') return false
      if (filter === 'escrow' && !['escrow_freeze', 'escrow_release'].includes(tx.type)) return false
      if (filter === 'payout' && !['payout', 'payout_fee'].includes(tx.type)) return false
      if (
        search &&
        !`${meta.label} ${tx.description ?? ''}`.toLowerCase().includes(search.toLowerCase())
      ) {
        return false
      }
      return true
    })
  }, [data, filter, period, search])

  const totals = useMemo(() => {
    let inc = 0
    let out = 0
    for (const tx of filtered) {
      const meta = getMeta(tx.type)
      if (tx.status === 'canceled' || tx.status === 'failed') continue
      const amt = Number(tx.amount)
      if (meta.incoming) inc += amt
      else out += amt
    }
    return { inc, out, net: inc - out, count: filtered.length }
  }, [filtered])

  const groups = useMemo(() => {
    const map = new Map<string, TransactionItem[]>()
    for (const tx of filtered) {
      const k = dayKey(tx.created_at)
      const arr = map.get(k) ?? []
      arr.push(tx)
      map.set(k, arr)
    }
    return Array.from(map.entries())
  }, [filtered])

  const balanceRub = Number(user?.balance_rub ?? 0)

  if (isLoading) {
    return (
      <div className="max-w-[1280px] mx-auto space-y-4">
        <Skeleton className="h-16" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-20" />
          ))}
        </div>
        <Skeleton className="h-16" />
        <Skeleton className="h-40" />
      </div>
    )
  }

  if (isError || !data) {
    return (
      <div className="max-w-[1280px] mx-auto space-y-4">
        <Notification type="danger">Не удалось загрузить историю</Notification>
        <Button variant="secondary" fullWidth onClick={() => refetch()}>
          Повторить
        </Button>
      </div>
    )
  }

  return (
    <div className="max-w-[1280px] mx-auto">
      <ScreenHeader
        title="История операций"
        subtitle="Все движения по балансу: пополнения, эскроу, выплаты и корректировки"
        action={
          <>
            <Button variant="secondary" iconLeft="export">
              Экспорт CSV
            </Button>
            <Button variant="secondary" iconLeft="docs">
              Экспорт PDF
            </Button>
          </>
        }
      />

      <div className="grid gap-3.5 mb-5" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
        <SummaryTile
          icon="arrow-down"
          tone="success"
          label="Поступления"
          value={`+ ${fmtRub(totals.inc)}`}
          delta={`${totals.count} операций`}
        />
        <SummaryTile
          icon="arrow-up"
          tone="danger"
          label="Списания"
          value={`− ${fmtRub(totals.out)}`}
          delta="За выбранный период"
        />
        <SummaryTile
          icon="wave"
          tone="accent"
          label="Нетто"
          value={(totals.net >= 0 ? '+ ' : '− ') + fmtRub(Math.abs(totals.net))}
          delta={`${totals.count} операций`}
        />
        <SummaryTile
          icon="wallet"
          tone="accent2"
          label="Текущий баланс"
          value={fmtRub(balanceRub)}
          delta="Доступно для эскроу"
        />
      </div>

      <div className="bg-harbor-card border border-border rounded-xl p-3.5 mb-3.5 flex items-center gap-3 flex-wrap">
        <div className="flex-1 min-w-[260px] flex items-center gap-2 px-3 py-2 rounded-lg bg-harbor-elevated border border-border">
          <Icon name="search" size={15} className="text-text-tertiary" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Поиск по описанию или заявке"
            className="flex-1 bg-transparent border-0 outline-none text-text-primary text-[13px] placeholder:text-text-tertiary"
          />
        </div>

        <div className="flex p-[3px] rounded-lg bg-harbor-elevated border border-border">
          {PERIODS.map((p) => {
            const on = period === p.id
            return (
              <button
                key={p.id}
                onClick={() => setPeriod(p.id)}
                className={`px-3 py-1.5 text-xs font-semibold rounded-[5px] transition-colors ${
                  on
                    ? 'bg-harbor-card text-text-primary shadow-sm'
                    : 'text-text-secondary hover:text-text-primary'
                }`}
              >
                {p.label}
              </button>
            )
          })}
        </div>

        <div className="flex gap-1.5 flex-wrap">
          {FILTERS.map((f) => {
            const on = filter === f.id
            return (
              <button
                key={f.id}
                onClick={() => setFilter(f.id)}
                className={`px-3 py-1.5 text-xs font-medium rounded-2xl border transition-all ${
                  on
                    ? 'border-accent bg-accent-muted text-accent'
                    : 'border-border bg-transparent text-text-secondary hover:border-border-active'
                }`}
              >
                {f.label}
              </button>
            )
          })}
        </div>
      </div>

      {groups.length === 0 ? (
        <div className="bg-harbor-card border border-dashed border-border rounded-xl p-[60px] text-center">
          <div className="inline-grid place-items-center w-14 h-14 rounded-[14px] bg-harbor-elevated text-text-tertiary mb-3.5">
            <Icon name="receipt" size={22} />
          </div>
          <div className="font-display text-base font-semibold text-text-primary mb-1">
            Ничего не найдено
          </div>
          <div className="text-[13px] text-text-secondary">
            Поменяйте фильтры или очистите строку поиска
          </div>
        </div>
      ) : (
        groups.map(([day, items]) => (
          <div key={day} className="mb-5">
            <div className="text-[11px] font-bold uppercase tracking-[0.09em] text-text-tertiary py-2 px-0.5 pb-2.5 flex items-center gap-2.5">
              <span>{day}</span>
              <span className="flex-1 h-px bg-border" />
              <span className="font-mono tabular-nums text-text-tertiary font-medium text-[11px]">
                {items.length} операций
              </span>
            </div>

            <div className="bg-harbor-card border border-border rounded-xl overflow-hidden">
              {items.map((tx, i) => (
                <TxRow key={tx.id} tx={tx} isLast={i === items.length - 1} />
              ))}
            </div>
          </div>
        ))
      )}

      {data.pages > 1 && (
        <div className="flex items-center justify-between mt-5 py-3.5 px-[18px] rounded-[10px] border border-border bg-harbor-card">
          <Button
            variant="ghost"
            size="sm"
            iconLeft="arrow-left"
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            Назад
          </Button>
          <div className="flex items-center gap-2.5 text-[12.5px] text-text-secondary">
            <span>Страница</span>
            <span className="font-mono font-semibold text-text-primary py-0.5 px-2.5 rounded-md bg-harbor-elevated border border-border">
              {page}
            </span>
            <span>из {data.pages}</span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            iconRight="arrow-right"
            disabled={page >= data.pages}
            onClick={() => setPage((p) => p + 1)}
          >
            Вперёд
          </Button>
        </div>
      )}
    </div>
  )
}

const toneIconBg: Record<'success' | 'danger' | 'accent' | 'accent2', string> = {
  success: 'bg-success-muted text-success',
  danger: 'bg-danger-muted text-danger',
  accent: 'bg-accent-muted text-accent',
  accent2: 'bg-accent-2-muted text-accent-2',
}

function SummaryTile({
  icon,
  tone,
  label,
  value,
  delta,
}: {
  icon: IconName
  tone: 'success' | 'danger' | 'accent' | 'accent2'
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
        <div className="text-[11.5px] text-text-tertiary mt-0.5">{delta}</div>
      </div>
    </div>
  )
}

const accentRowBg: Record<AccentKey, string> = {
  info: 'bg-info-muted text-info border-info/15',
  success: 'bg-success-muted text-success border-success/15',
  warning: 'bg-warning-muted text-warning border-warning/15',
  danger: 'bg-danger-muted text-danger border-danger/15',
  neutral: 'bg-harbor-elevated text-text-secondary border-border',
}

const statusPillClass: Record<string, string> = {
  completed: 'bg-success-muted text-success',
  succeeded: 'bg-success-muted text-success',
  pending: 'bg-warning-muted text-warning',
  canceled: 'bg-harbor-elevated text-text-tertiary',
  failed: 'bg-danger-muted text-danger',
}

function TxRow({ tx, isLast }: { tx: TransactionItem; isLast: boolean }) {
  const meta = getMeta(tx.type)
  const statusText = STATUS_LABEL[tx.status] ?? tx.status
  const isStrike = tx.status === 'canceled' || tx.status === 'failed'
  const amountColor = isStrike
    ? 'text-text-tertiary'
    : meta.incoming
      ? 'text-success'
      : 'text-text-primary'
  const sign = isStrike ? '' : meta.incoming ? '+ ' : '− '

  return (
    <div
      className={`grid gap-3.5 px-[18px] py-3.5 items-center hover:bg-harbor-elevated/40 transition-colors cursor-pointer ${
        isLast ? '' : 'border-b border-border'
      }`}
      style={{ gridTemplateColumns: '44px 1fr auto auto' }}
    >
      <span
        className={`w-10 h-10 rounded-[10px] grid place-items-center border ${accentRowBg[meta.accent]}`}
      >
        <Icon name={meta.icon} size={17} />
      </span>

      <div className="min-w-0">
        <div className="flex items-baseline gap-2.5 mb-0.5">
          <span className="text-[13.5px] font-semibold text-text-primary">{meta.label}</span>
          {tx.placement_request_id && (
            <span className="font-mono text-[11px] text-text-tertiary py-px px-1.5 rounded bg-harbor-elevated">
              #{tx.placement_request_id}
            </span>
          )}
        </div>
        {tx.description && (
          <div className="text-xs text-text-secondary truncate">{tx.description}</div>
        )}
        <div className="text-[11.5px] text-text-tertiary mt-0.5 tabular-nums">
          {fmtDateTime(tx.created_at)} МСК
        </div>
      </div>

      <span
        className={`text-[10.5px] font-bold tracking-[0.08em] uppercase py-1 px-2 rounded whitespace-nowrap ${statusPillClass[tx.status] ?? 'bg-harbor-elevated text-text-secondary'}`}
      >
        {statusText}
      </span>

      <span
        className={`font-mono tabular-nums text-[15px] font-semibold whitespace-nowrap text-right min-w-[120px] ${amountColor} ${isStrike ? 'line-through' : ''}`}
      >
        {sign}
        {fmtRub(Number(tx.amount))}
      </span>
    </div>
  )
}
