import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Icon } from '@shared/ui'
import { useTransactionHistory } from '@/hooks/useBillingQueries'
import { useMyPlacements } from '@/hooks/useCampaignQueries'
import type { TransactionItem } from '@/api/billing'

type Tab = 'transactions' | 'campaigns'

function formatRelative(iso: string): string {
  const then = new Date(iso)
  const diffMin = Math.round((Date.now() - then.getTime()) / 60000)
  if (diffMin < 60) return `${Math.max(diffMin, 1)} мин`
  const diffHr = Math.round(diffMin / 60)
  if (diffHr < 24) return then.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
  const diffDay = Math.round(diffHr / 24)
  if (diffDay === 1) return 'вчера'
  if (diffDay < 7) return `${diffDay} д`
  return then.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' })
}

function TransactionRow({ tx }: { tx: TransactionItem }) {
  const isIncome = tx.type === 'topup' || tx.type === 'bonus' || tx.type === 'refund_full' || tx.type === 'escrow_release'
  const isHold = tx.type === 'escrow_freeze'
  const sign = isIncome ? '+' : '−'
  const amount = `${sign}${parseFloat(tx.amount).toLocaleString('ru-RU', { maximumFractionDigits: 0 })} ₽`
  const amountClr = isIncome ? 'text-success' : isHold ? 'text-warning' : 'text-text-primary'
  const iconBg = isIncome ? 'bg-success-muted text-success' : isHold ? 'bg-warning-muted text-warning' : 'bg-harbor-secondary text-danger'
  const iconName = isIncome ? 'arrow-down' : isHold ? 'clock' : 'arrow-up'

  return (
    <div className="grid grid-cols-[36px_1fr_auto_auto] items-center gap-3.5 px-4 py-2.5 border-t border-border first:border-t-0">
      <div className={`w-8 h-8 rounded-md grid place-items-center ${iconBg}`}>
        <Icon name={iconName} size={14} />
      </div>
      <div className="min-w-0">
        <div className="text-[13px] font-medium text-text-primary truncate">
          {tx.description ?? (isIncome ? 'Пополнение' : 'Списание')}
        </div>
        <div className="text-[11px] text-text-tertiary mt-0.5 truncate">
          {tx.type}
        </div>
      </div>
      <div className="text-[11.5px] text-text-tertiary font-mono">{formatRelative(tx.created_at)}</div>
      <div className={`font-mono text-[13.5px] font-semibold tabular-nums min-w-[90px] text-right ${amountClr}`}>
        {amount}
      </div>
    </div>
  )
}

function CampaignRow({ p }: { p: { id: number; status?: string; final_price?: string | null; proposed_price?: string; channel?: { title?: string | null; username?: string | null } | null; ad_text?: string } }) {
  const navigate = useNavigate()
  const status = p.status ?? 'pending_owner'
  const statusMap: Record<string, { label: string; clr: string }> = {
    published: { label: 'Опубликована', clr: 'bg-success-muted text-success' },
    escrow: { label: 'В эскроу', clr: 'bg-info-muted text-info' },
    pending_payment: { label: 'Оплата', clr: 'bg-warning-muted text-warning' },
    pending_owner: { label: 'Модерация', clr: 'bg-warning-muted text-warning' },
    counter_offer: { label: 'Контроферта', clr: 'bg-accent-2-muted text-accent-2' },
    completed: { label: 'Завершена', clr: 'bg-harbor-secondary text-text-tertiary' },
    cancelled: { label: 'Отменена', clr: 'bg-harbor-secondary text-text-tertiary' },
    refunded: { label: 'Возврат', clr: 'bg-harbor-secondary text-text-tertiary' },
    failed: { label: 'Ошибка', clr: 'bg-danger-muted text-danger' },
    failed_permissions: { label: 'Нет прав', clr: 'bg-danger-muted text-danger' },
  }
  const s = statusMap[status] ?? statusMap.pending_owner
  const price = parseFloat(p.final_price ?? p.proposed_price ?? '0')
  const channelLabel = p.channel?.title || (p.channel?.username ? `@${p.channel.username}` : `#${p.id}`)

  return (
    <button
      type="button"
      onClick={() => navigate(`/adv/campaigns/${p.id}/waiting`)}
      className="w-full grid grid-cols-[1.4fr_140px_auto] gap-3.5 items-center px-4 py-2.5 border-t border-border first:border-t-0 text-left hover:bg-harbor-secondary transition-colors cursor-pointer"
    >
      <div>
        <div className="text-[13px] font-medium text-text-primary truncate">{channelLabel}</div>
        <div className="text-[11px] text-text-tertiary mt-0.5 truncate">
          {p.ad_text?.slice(0, 48) ?? 'Без описания'}
        </div>
      </div>
      <div className={`justify-self-start text-[10.5px] font-semibold uppercase tracking-[0.05em] px-2 py-0.5 rounded ${s.clr}`}>
        {s.label}
      </div>
      <div className="font-mono text-[13px] font-semibold tabular-nums text-text-primary text-right">
        {price.toLocaleString('ru-RU', { maximumFractionDigits: 0 })} ₽
      </div>
    </button>
  )
}

export function RecentActivity() {
  const [tab, setTab] = useState<Tab>('transactions')
  const navigate = useNavigate()
  const { data: txData, isLoading: txLoading } = useTransactionHistory(1, 5)
  const { data: campaigns, isLoading: campLoading } = useMyPlacements('advertiser')

  const txs: TransactionItem[] = useMemo(() => txData?.items ?? [], [txData?.items])
  const recentCampaigns = useMemo(
    () => (Array.isArray(campaigns) ? (campaigns as unknown as Array<{ id: number }>).slice(0, 5) : []),
    [campaigns],
  )

  return (
    <section className="rounded-xl bg-harbor-card border border-border overflow-hidden">
      <header className="flex items-center gap-1 px-5 py-3 border-b border-border">
        <h3 className="font-display text-sm font-semibold text-text-primary mr-4">Активность</h3>
        {(
          [
            { id: 'transactions' as Tab, label: 'Транзакции', count: txs.length },
            { id: 'campaigns' as Tab, label: 'Кампании', count: recentCampaigns.length },
          ] as const
        ).map((t) => {
          const on = tab === t.id
          return (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={`px-3 py-1.5 text-[12.5px] font-semibold rounded-md transition-colors inline-flex items-center gap-1.5 ${
                on ? 'bg-harbor-secondary text-text-primary' : 'text-text-secondary hover:text-text-primary cursor-pointer'
              }`}
            >
              {t.label}
              <span
                className={`text-[10px] font-mono px-1.5 rounded-full ${
                  on ? 'bg-harbor-elevated text-text-tertiary' : 'bg-harbor-secondary text-text-tertiary'
                }`}
              >
                {t.count}
              </span>
            </button>
          )
        })}
        <div className="flex-1" />
        <button
          type="button"
          onClick={() => navigate(tab === 'transactions' ? '/billing/history' : '/adv/campaigns')}
          className="flex items-center gap-1 text-[12px] text-accent hover:text-accent-hover cursor-pointer"
        >
          Все <Icon name="chevron-right" size={12} />
        </button>
      </header>

      <div>
        {tab === 'transactions' ? (
          txLoading ? (
            <div className="px-5 py-6 text-[12.5px] text-text-tertiary">Загружаем…</div>
          ) : txs.length === 0 ? (
            <div className="px-5 py-6 text-[12.5px] text-text-tertiary">Нет транзакций.</div>
          ) : (
            txs.map((tx) => <TransactionRow key={tx.id} tx={tx} />)
          )
        ) : campLoading ? (
          <div className="px-5 py-6 text-[12.5px] text-text-tertiary">Загружаем…</div>
        ) : recentCampaigns.length === 0 ? (
          <div className="px-5 py-6 text-[12.5px] text-text-tertiary">Нет кампаний.</div>
        ) : (
          recentCampaigns.map((p) => <CampaignRow key={p.id} p={p as Parameters<typeof CampaignRow>[0]['p']} />)
        )}
      </div>
    </section>
  )
}
