import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Button,
  Skeleton,
  EmptyState,
  Icon,
  ScreenHeader,
} from '@shared/ui'
import type { IconName } from '@shared/ui'
import { formatCurrency, formatDateMSK, formatDateTimeMSK } from '@/lib/constants'
import { useMyPlacements } from '@/hooks/useCampaignQueries'

type Filter = 'new' | 'active' | 'completed' | 'cancelled'
type SortKey = 'date' | 'price'
type SortDir = 'asc' | 'desc'

const NEW_STATUSES = ['pending_owner', 'counter_offer', 'pending_payment']
const ACTIVE_STATUSES = ['escrow']
const COMPLETED_STATUSES = ['published']
const CANCELLED_STATUSES = ['cancelled', 'refunded', 'failed', 'failed_permissions']
const PAGE_SIZE = 10

function getFilter(status: string): Filter {
  if (NEW_STATUSES.includes(status)) return 'new'
  if (ACTIVE_STATUSES.includes(status)) return 'active'
  if (COMPLETED_STATUSES.includes(status)) return 'completed'
  if (CANCELLED_STATUSES.includes(status)) return 'cancelled'
  return 'cancelled'
}

const EMPTY_SUBTITLE: Record<Filter, string> = {
  new: 'Новые заявки появятся, когда рекламодатели отправят запросы на ваш канал.',
  active: 'Нет активных размещений',
  completed: 'Нет завершённых размещений',
  cancelled: 'Нет отменённых заявок',
}

type Tone = 'info' | 'warning' | 'success' | 'neutral' | 'danger' | 'accent2'

const STATUS_META: Record<string, { label: string; tone: Tone; icon: IconName }> = {
  pending_owner: { label: 'Новая', tone: 'warning', icon: 'hourglass' },
  counter_offer: { label: 'Контр-оферта', tone: 'accent2', icon: 'refresh' },
  pending_payment: { label: 'Ожидает оплаты', tone: 'warning', icon: 'card' },
  escrow: { label: 'В эскроу', tone: 'info', icon: 'lock' },
  published: { label: 'Опубликован', tone: 'success', icon: 'check' },
  cancelled: { label: 'Отменён', tone: 'neutral', icon: 'close' },
  refunded: { label: 'Возврат', tone: 'neutral', icon: 'refund' },
  failed: { label: 'Ошибка', tone: 'danger', icon: 'error' },
  failed_permissions: { label: 'Нет прав', tone: 'danger', icon: 'blocked' },
}

const toneClasses: Record<Tone, string> = {
  info: 'bg-info-muted text-info',
  warning: 'bg-warning-muted text-warning',
  success: 'bg-success-muted text-success',
  neutral: 'bg-harbor-elevated text-text-tertiary',
  danger: 'bg-danger-muted text-danger',
  accent2: 'bg-accent-2-muted text-accent-2',
}

function getStatusMeta(status: string) {
  return STATUS_META[status] ?? { label: status, tone: 'neutral' as Tone, icon: 'info' as IconName }
}

export default function OwnRequests() {
  const navigate = useNavigate()
  const [filter, setFilter] = useState<Filter>('new')
  const [sortKey, setSortKey] = useState<SortKey>('date')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [page, setPage] = useState(0)
  const { data: requests = [], isLoading, refetch } = useMyPlacements('owner')

  const counts = useMemo(() => {
    const newCount = requests.filter((r) => getFilter(r.status) === 'new').length
    const activeCount = requests.filter((r) => getFilter(r.status) === 'active').length
    const completedCount = requests.filter((r) => getFilter(r.status) === 'completed').length
    const cancelledCount = requests.filter((r) => getFilter(r.status) === 'cancelled').length
    const pendingOwnerEarn = requests
      .filter((r) => r.status === 'pending_owner')
      .reduce(
        (s, r) => s + parseFloat(String(r.proposed_price ?? '0')) * 0.85,
        0,
      )
    return { newCount, activeCount, completedCount, cancelledCount, pendingOwnerEarn }
  }, [requests])

  const filtered = requests.filter((r) => getFilter(r.status) === filter)

  const sorted = useMemo(() => {
    const arr = [...filtered]
    arr.sort((a, b) => {
      if (sortKey === 'price') {
        const aP = parseFloat(String(a.final_price ?? a.counter_price ?? a.proposed_price ?? '0'))
        const bP = parseFloat(String(b.final_price ?? b.counter_price ?? b.proposed_price ?? '0'))
        return sortDir === 'asc' ? aP - bP : bP - aP
      }
      const aD = a.proposed_schedule ? new Date(a.proposed_schedule).getTime()
        : a.created_at ? new Date(a.created_at).getTime() : 0
      const bD = b.proposed_schedule ? new Date(b.proposed_schedule).getTime()
        : b.created_at ? new Date(b.created_at).getTime() : 0
      return sortDir === 'asc' ? aD - bD : bD - aD
    })
    return arr
  }, [filtered, sortKey, sortDir])

  const totalPages = Math.ceil(sorted.length / PAGE_SIZE)
  const paged = sorted.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else {
      setSortKey(key)
      setSortDir('desc')
    }
    setPage(0)
  }

  const handleFilterChange = (f: Filter) => {
    setFilter(f)
    setPage(0)
  }

  return (
    <div className="max-w-[1280px] mx-auto">
      <ScreenHeader
        title="Входящие заявки"
        subtitle="Рассматривайте, принимайте или делайте контр-оферту на новые запросы размещений"
        action={
          <Button
            variant="ghost"
            size="sm"
            icon
            onClick={() => void refetch()}
            title="Обновить"
            aria-label="Обновить"
          >
            <Icon name="refresh" size={14} />
          </Button>
        }
      />

      <div
        className="grid gap-3.5 mb-5"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}
      >
        <SummaryTile
          icon="hourglass"
          tone="warning"
          label="Ждут ответа"
          value={String(counts.newCount)}
          delta="На принятие есть 24 ч"
        />
        <SummaryTile
          icon="ruble"
          tone="accent2"
          label="Потенциал (85%)"
          value={formatCurrency(counts.pendingOwnerEarn)}
          delta="По ожидающим заявкам"
        />
        <SummaryTile
          icon="check"
          tone="success"
          label="Завершено"
          value={String(counts.completedCount)}
          delta="Опубликованные размещения"
        />
        <SummaryTile
          icon="close"
          tone="neutral"
          label="Отменено"
          value={String(counts.cancelledCount)}
          delta="Включая возвраты"
        />
      </div>

      <div className="bg-harbor-card border border-border rounded-xl p-3.5 mb-3.5 flex items-center gap-3 flex-wrap">
        <div className="flex gap-1.5 flex-wrap">
          <FilterPill
            active={filter === 'new'}
            tone="warning"
            onClick={() => handleFilterChange('new')}
          >
            Новые <span className="font-mono tabular-nums text-[11px] opacity-80">{counts.newCount}</span>
          </FilterPill>
          <FilterPill
            active={filter === 'active'}
            tone="success"
            onClick={() => handleFilterChange('active')}
          >
            Активные <span className="font-mono tabular-nums text-[11px] opacity-80">{counts.activeCount}</span>
          </FilterPill>
          <FilterPill
            active={filter === 'completed'}
            tone="success"
            onClick={() => handleFilterChange('completed')}
          >
            Завершённые <span className="font-mono tabular-nums text-[11px] opacity-80">{counts.completedCount}</span>
          </FilterPill>
          <FilterPill
            active={filter === 'cancelled'}
            tone="neutral"
            onClick={() => handleFilterChange('cancelled')}
          >
            Отменённые <span className="font-mono tabular-nums text-[11px] opacity-80">{counts.cancelledCount}</span>
          </FilterPill>
        </div>

        <div className="flex-1" />

        <div className="flex items-center gap-1 text-[12px] text-text-tertiary">
          <span>Сортировка:</span>
          <SortBtn active={sortKey === 'date'} dir={sortDir} onClick={() => toggleSort('date')}>
            Дата
          </SortBtn>
          <SortBtn active={sortKey === 'price'} dir={sortDir} onClick={() => toggleSort('price')}>
            Цена
          </SortBtn>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-16" />
          <Skeleton className="h-16" />
          <Skeleton className="h-16" />
        </div>
      ) : sorted.length === 0 ? (
        <EmptyState
          icon="requests"
          title="Нет заявок"
          description={EMPTY_SUBTITLE[filter]}
        />
      ) : (
        <>
          <div className="bg-harbor-card border border-border rounded-xl overflow-hidden">
            {paged.map((req, i) => {
              const meta = getStatusMeta(req.status)
              const isActionable = ['pending_owner', 'counter_offer'].includes(req.status)
              const dateStr = req.proposed_schedule
                ? formatDateTimeMSK(req.proposed_schedule)
                : formatDateMSK(req.created_at)
              const priceStr = formatCurrency(
                req.final_price ?? req.counter_price ?? req.proposed_price,
              )
              const channelLabel = req.channel?.username
                ? `@${req.channel.username}`
                : `#${req.channel_id}`

              return (
                <div
                  key={req.id}
                  className={`flex items-center gap-4 px-[18px] py-3.5 hover:bg-harbor-elevated/40 transition-colors ${i === paged.length - 1 ? '' : 'border-b border-border'}`}
                >
                  <span
                    className={`grid place-items-center w-10 h-10 rounded-[10px] flex-shrink-0 ${toneClasses[meta.tone]}`}
                  >
                    <Icon name={meta.icon} size={16} />
                  </span>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-baseline gap-2.5 mb-0.5 flex-wrap">
                      <span className="text-[13.5px] font-semibold text-text-primary">
                        {channelLabel}
                      </span>
                      <span className="font-mono text-[11px] text-text-tertiary py-px px-1.5 rounded bg-harbor-elevated">
                        #{req.id}
                      </span>
                    </div>
                    <div className="text-xs text-text-secondary truncate max-w-[420px]">
                      {req.ad_text.substring(0, 100)}
                      {req.ad_text.length > 100 ? '…' : ''}
                    </div>
                    <div className="text-[11.5px] text-text-tertiary mt-0.5 tabular-nums">
                      {dateStr} МСК
                    </div>
                  </div>

                  <span
                    className={`hidden sm:inline-flex text-[10.5px] font-bold tracking-[0.08em] uppercase py-1 px-2 rounded whitespace-nowrap ${toneClasses[meta.tone]}`}
                  >
                    {meta.label}
                  </span>

                  <span className="font-mono tabular-nums text-[15px] font-semibold whitespace-nowrap text-right min-w-[110px] text-text-primary">
                    {priceStr}
                  </span>

                  <div className="flex gap-1.5 flex-shrink-0">
                    <Button
                      variant={isActionable ? 'primary' : 'secondary'}
                      size="sm"
                      iconRight="arrow-right"
                      onClick={() => navigate(`/own/requests/${req.id}`)}
                    >
                      {isActionable ? 'Ответить' : 'Открыть'}
                    </Button>
                  </div>
                </div>
              )
            })}
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-5 py-3.5 px-[18px] rounded-[10px] border border-border bg-harbor-card">
              <Button
                variant="ghost"
                size="sm"
                iconLeft="arrow-left"
                disabled={page === 0}
                onClick={() => setPage((p) => p - 1)}
              >
                Назад
              </Button>
              <div className="flex items-center gap-2.5 text-[12.5px] text-text-secondary">
                <span>Страница</span>
                <span className="font-mono font-semibold text-text-primary py-0.5 px-2.5 rounded-md bg-harbor-elevated border border-border">
                  {page + 1}
                </span>
                <span>из {totalPages}</span>
              </div>
              <Button
                variant="ghost"
                size="sm"
                iconRight="arrow-right"
                disabled={page + 1 >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Вперёд
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  )
}

const toneIconBg: Record<'success' | 'warning' | 'accent2' | 'neutral', string> = {
  success: 'bg-success-muted text-success',
  warning: 'bg-warning-muted text-warning',
  accent2: 'bg-accent-2-muted text-accent-2',
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
  tone: 'success' | 'warning' | 'accent2' | 'neutral'
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

const pillTone: Record<'warning' | 'success' | 'neutral', { on: string; off: string }> = {
  warning: {
    on: 'border-warning bg-warning-muted text-warning',
    off: 'border-border bg-transparent text-text-secondary hover:border-border-active',
  },
  success: {
    on: 'border-success bg-success-muted text-success',
    off: 'border-border bg-transparent text-text-secondary hover:border-border-active',
  },
  neutral: {
    on: 'border-border-active bg-harbor-elevated text-text-primary',
    off: 'border-border bg-transparent text-text-secondary hover:border-border-active',
  },
}

function FilterPill({
  active,
  tone,
  onClick,
  children,
}: {
  active: boolean
  tone: 'warning' | 'success' | 'neutral'
  onClick: () => void
  children: React.ReactNode
}) {
  const cls = active ? pillTone[tone].on : pillTone[tone].off
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded-2xl border transition-all ${cls}`}
    >
      {children}
    </button>
  )
}

function SortBtn({
  active,
  dir,
  onClick,
  children,
}: {
  active: boolean
  dir: SortDir
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center gap-1 px-2 py-1 rounded-md transition-colors ${
        active ? 'bg-harbor-elevated text-text-primary' : 'text-text-secondary hover:text-text-primary'
      }`}
    >
      {children}
      {active && <Icon name={dir === 'asc' ? 'sort-asc' : 'sort-desc'} size={12} />}
      {!active && <Icon name="sort" size={12} className="opacity-60" />}
    </button>
  )
}
