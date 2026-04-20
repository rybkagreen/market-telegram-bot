import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Button,
  Skeleton,
  EmptyState,
  Icon,
  ScreenHeader,
  Notification,
} from '@shared/ui'
import type { IconName } from '@shared/ui'
import { formatCurrency, formatDateTimeMSK, formatDateMSK } from '@/lib/constants'
import { useMyPlacements, useUpdatePlacement } from '@/hooks/useCampaignQueries'

type Filter = 'active' | 'completed' | 'cancelled'
type SortKey = 'date' | 'price'
type SortDir = 'asc' | 'desc'

const ACTIVE_STATUSES = ['pending_owner', 'counter_offer', 'pending_payment', 'escrow']
const COMPLETED_STATUSES = ['published']
const CANCELLED_STATUSES = ['cancelled', 'refunded', 'failed', 'failed_permissions']
const PAGE_SIZE = 10

function getFilter(status: string): Filter {
  if (ACTIVE_STATUSES.includes(status)) return 'active'
  if (COMPLETED_STATUSES.includes(status)) return 'completed'
  if (CANCELLED_STATUSES.includes(status)) return 'cancelled'
  return 'cancelled'
}

const EMPTY_SUBTITLE: Record<Filter, string> = {
  active: 'Нет активных кампаний — создайте первую',
  completed: 'Нет завершённых кампаний',
  cancelled: 'Нет отменённых кампаний',
}

type StatusKey =
  | 'pending_owner'
  | 'counter_offer'
  | 'pending_payment'
  | 'escrow'
  | 'published'
  | 'cancelled'
  | 'refunded'
  | 'failed'
  | 'failed_permissions'

type StatusTone = 'info' | 'warning' | 'success' | 'neutral' | 'danger' | 'accent2'

const STATUS_META: Record<StatusKey, { label: string; tone: StatusTone; icon: IconName }> = {
  pending_owner: { label: 'Ожидает владельца', tone: 'warning', icon: 'hourglass' },
  counter_offer: { label: 'Контр-оферта', tone: 'accent2', icon: 'refresh' },
  pending_payment: { label: 'Ожидает оплаты', tone: 'warning', icon: 'card' },
  escrow: { label: 'В эскроу', tone: 'info', icon: 'lock' },
  published: { label: 'Опубликован', tone: 'success', icon: 'check' },
  cancelled: { label: 'Отменён', tone: 'neutral', icon: 'close' },
  refunded: { label: 'Возврат', tone: 'neutral', icon: 'refund' },
  failed: { label: 'Ошибка', tone: 'danger', icon: 'error' },
  failed_permissions: { label: 'Нет прав', tone: 'danger', icon: 'blocked' },
}

const toneClasses: Record<StatusTone, string> = {
  info: 'bg-info-muted text-info',
  warning: 'bg-warning-muted text-warning',
  success: 'bg-success-muted text-success',
  neutral: 'bg-harbor-elevated text-text-tertiary',
  danger: 'bg-danger-muted text-danger',
  accent2: 'bg-accent-2-muted text-accent-2',
}

function getStatusMeta(status: string) {
  return STATUS_META[status as StatusKey] ?? { label: status, tone: 'neutral' as StatusTone, icon: 'info' as IconName }
}

export default function MyCampaigns() {
  const navigate = useNavigate()
  const [filter, setFilter] = useState<Filter>('active')
  const [sortKey, setSortKey] = useState<SortKey>('date')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [page, setPage] = useState(0)
  const { data: placements = [], isLoading, refetch } = useMyPlacements('advertiser')
  const { mutate: updatePlacement, isPending: cancelling, variables: cancellingVars } = useUpdatePlacement()

  const now = useMemo(() => new Date(), [])
  const isExpired = (p: { expires_at?: string | null; status: string }) =>
    !!p.expires_at && new Date(p.expires_at) < now && ACTIVE_STATUSES.includes(p.status)

  const counts = useMemo(() => {
    const all = placements.length
    const active = placements.filter((p) => getFilter(p.status) === 'active').length
    const completed = placements.filter((p) => getFilter(p.status) === 'completed').length
    const cancelled = placements.filter((p) => getFilter(p.status) === 'cancelled').length
    const totalSpent = placements
      .filter((p) => getFilter(p.status) === 'completed')
      .reduce((sum, p) => sum + Number(p.final_price ?? p.counter_price ?? p.proposed_price ?? 0), 0)
    return { all, active, completed, cancelled, totalSpent }
  }, [placements])

  const filtered = placements.filter((p) => getFilter(p.status) === filter)

  const sorted = useMemo(() => {
    const arr = [...filtered]
    arr.sort((a, b) => {
      if (sortKey === 'price') {
        const aP = parseFloat(String(a.final_price ?? a.counter_price ?? a.proposed_price ?? '0'))
        const bP = parseFloat(String(b.final_price ?? b.counter_price ?? b.proposed_price ?? '0'))
        return sortDir === 'asc' ? aP - bP : bP - aP
      }
      const aD = a.proposed_schedule
        ? new Date(a.proposed_schedule).getTime()
        : a.created_at
        ? new Date(a.created_at).getTime()
        : 0
      const bD = b.proposed_schedule
        ? new Date(b.proposed_schedule).getTime()
        : b.created_at
        ? new Date(b.created_at).getTime()
        : 0
      return sortDir === 'asc' ? aD - bD : bD - aD
    })
    return arr
  }, [filtered, sortKey, sortDir])

  const totalPages = Math.ceil(sorted.length / PAGE_SIZE)
  const paged = sorted.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
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
        crumbs={['Главная', 'Рекламодатель', 'Мои кампании']}
        title="Мои кампании"
        subtitle="Запросы на размещение, модерация, эскроу и публикации"
        action={
          <div className="flex gap-2">
            <Button variant="secondary" iconLeft="refresh" onClick={() => void refetch()}>
              Обновить
            </Button>
            <Button
              variant="primary"
              iconLeft="plus"
              onClick={() => navigate('/adv/campaigns/new/category')}
            >
              Создать кампанию
            </Button>
          </div>
        }
      />

      <div
        className="grid gap-3.5 mb-5"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}
      >
        <SummaryTile
          icon="campaign"
          tone="accent"
          label="Всего"
          value={String(counts.all)}
          delta={`${counts.active} активных сейчас`}
        />
        <SummaryTile
          icon="hourglass"
          tone="warning"
          label="В работе"
          value={String(counts.active)}
          delta="Модерация / эскроу / ожидание"
        />
        <SummaryTile
          icon="check"
          tone="success"
          label="Завершено"
          value={String(counts.completed)}
          delta={`${formatCurrency(counts.totalSpent)} потрачено`}
        />
        <SummaryTile
          icon="close"
          tone="neutral"
          label="Отменено"
          value={String(counts.cancelled)}
          delta="Включая возвраты и ошибки"
        />
      </div>

      <div className="bg-harbor-card border border-border rounded-xl p-3.5 mb-3.5 flex items-center gap-3 flex-wrap">
        <div className="flex gap-1.5 flex-wrap">
          <FilterPill active={filter === 'active'} tone="warning" onClick={() => handleFilterChange('active')}>
            Активные
            <span className="font-mono tabular-nums text-[11px] opacity-80">{counts.active}</span>
          </FilterPill>
          <FilterPill active={filter === 'completed'} tone="success" onClick={() => handleFilterChange('completed')}>
            Завершённые
            <span className="font-mono tabular-nums text-[11px] opacity-80">{counts.completed}</span>
          </FilterPill>
          <FilterPill active={filter === 'cancelled'} tone="neutral" onClick={() => handleFilterChange('cancelled')}>
            Отменённые
            <span className="font-mono tabular-nums text-[11px] opacity-80">{counts.cancelled}</span>
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
          icon="campaign"
          title="Нет кампаний"
          description={EMPTY_SUBTITLE[filter]}
          action={
            filter === 'active'
              ? { label: 'Создать кампанию', onClick: () => navigate('/adv/campaigns/new/category') }
              : undefined
          }
        />
      ) : (
        <>
          <div className="bg-harbor-card border border-border rounded-xl overflow-hidden">
            {paged.map((placement, i) => {
              const status = getStatusMeta(placement.status)
              const isCancellingThis =
                cancelling && (cancellingVars as { id?: number } | undefined)?.id === placement.id
              const price = formatCurrency(
                placement.final_price ?? placement.counter_price ?? placement.proposed_price,
              )
              const dateStr = placement.proposed_schedule
                ? formatDateTimeMSK(placement.proposed_schedule)
                : formatDateMSK(placement.created_at)
              const channelLabel = placement.channel?.username
                ? `@${placement.channel.username}`
                : `#${placement.channel_id}`
              const expired = isExpired(placement)

              return (
                <div
                  key={placement.id}
                  className={`flex items-center gap-4 px-[18px] py-3.5 hover:bg-harbor-elevated/40 transition-colors ${i === paged.length - 1 ? '' : 'border-b border-border'}`}
                >
                  <span
                    className={`grid place-items-center w-10 h-10 rounded-[10px] flex-shrink-0 ${toneClasses[status.tone]}`}
                  >
                    <Icon name={status.icon} size={16} />
                  </span>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-baseline gap-2.5 mb-0.5 flex-wrap">
                      <span className="text-[13.5px] font-semibold text-text-primary">
                        {channelLabel}
                      </span>
                      <span className="font-mono text-[11px] text-text-tertiary py-px px-1.5 rounded bg-harbor-elevated">
                        #{placement.id}
                      </span>
                      {expired && (
                        <span className="text-[11px] font-semibold uppercase tracking-[0.05em] text-warning">
                          Просрочена
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-text-secondary truncate max-w-[420px]">
                      {placement.ad_text.substring(0, 100)}
                      {placement.ad_text.length > 100 ? '…' : ''}
                    </div>
                    <div className="text-[11.5px] text-text-tertiary mt-0.5 tabular-nums">
                      {dateStr} МСК
                    </div>
                  </div>

                  <span
                    className={`hidden sm:inline-flex text-[10.5px] font-bold tracking-[0.08em] uppercase py-1 px-2 rounded whitespace-nowrap ${toneClasses[status.tone]}`}
                  >
                    {status.label}
                  </span>

                  <span className="font-mono tabular-nums text-[15px] font-semibold whitespace-nowrap text-right min-w-[110px] text-text-primary">
                    {price}
                  </span>

                  <div className="flex gap-1.5 flex-shrink-0">
                    {filter === 'active' && (
                      <>
                        <Button
                          variant="secondary"
                          size="sm"
                          icon
                          onClick={() => navigate(`/adv/campaigns/${placement.id}/waiting`)}
                          title="Детали"
                        >
                          <Icon name="eye" size={14} />
                        </Button>
                        <Button
                          variant="danger"
                          size="sm"
                          icon
                          disabled={isCancellingThis}
                          loading={isCancellingThis}
                          onClick={() =>
                            updatePlacement(
                              { id: placement.id, data: { action: 'cancel' } },
                              { onSuccess: () => void refetch() },
                            )
                          }
                          title="Отменить"
                        >
                          <Icon name="close" size={14} />
                        </Button>
                      </>
                    )}
                    {filter === 'completed' && (
                      <Button
                        variant="secondary"
                        size="sm"
                        icon
                        onClick={() => navigate(`/adv/campaigns/${placement.id}/published`)}
                        title="Результат"
                      >
                        <Icon name="analytics" size={14} />
                      </Button>
                    )}
                    {filter === 'cancelled' && (
                      <Button
                        variant="ghost"
                        size="sm"
                        icon
                        onClick={() => navigate(`/adv/campaigns/${placement.id}/waiting`)}
                        title="Просмотр"
                      >
                        <Icon name="eye" size={14} />
                      </Button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>

          {placements.some(isExpired) && filter === 'active' && (
            <div className="mt-3.5">
              <Notification type="warning">
                Кампании со статусом «Просрочена» будут автоматически отменены системой.
              </Notification>
            </div>
          )}

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

const toneIconBg: Record<'success' | 'warning' | 'accent' | 'neutral', string> = {
  success: 'bg-success-muted text-success',
  warning: 'bg-warning-muted text-warning',
  accent: 'bg-accent-muted text-accent',
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
  tone: 'success' | 'warning' | 'accent' | 'neutral'
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
