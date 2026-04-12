import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button, StatusPill, Skeleton, Notification, EmptyState, Card } from '@shared/ui'
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
  active: 'Нет активных кампаний — создайте первую!',
  completed: 'Нет завершённых кампаний',
  cancelled: 'Нет отменённых кампаний',
}

function formatDate(dt: string | null | undefined): string {
  return formatDateMSK(dt)
}

function formatSchedule(dt: string | null | undefined): string {
  return formatDateTimeMSK(dt)
}

function statusToPill(status: string): { status: 'success' | 'warning' | 'danger' | 'default'; label: string } {
  const map: Record<string, { status: 'success' | 'warning' | 'danger' | 'default'; label: string }> = {
    pending_owner: { status: 'warning', label: '⏳ Ожидает владельца' },
    counter_offer: { status: 'warning', label: '🔄 Контр-оферта' },
    pending_payment: { status: 'warning', label: '💳 Ожидает оплаты' },
    escrow: { status: 'warning', label: '🔒 Эскроу' },
    published: { status: 'success', label: '✅ Опубликован' },
    cancelled: { status: 'danger', label: '❌ Отменён' },
    refunded: { status: 'danger', label: '💸 Возврат' },
    failed: { status: 'danger', label: '⚠️ Ошибка' },
    failed_permissions: { status: 'danger', label: '⚠️ Нет прав' },
  }
  return map[status] ?? { status: 'default', label: status }
}

function SortIcon({ active, dir }: { active: boolean; dir: SortDir }) {
  if (!active) return <span className="text-text-tertiary ml-1">↕</span>
  return <span className="text-accent ml-1">{dir === 'asc' ? '↑' : '↓'}</span>
}

export default function MyCampaigns() {
  const navigate = useNavigate()
  const [filter, setFilter] = useState<Filter>('active')
  const [sortKey, setSortKey] = useState<SortKey>('date')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [page, setPage] = useState(0)
  // Always query as advertiser — this is the advertiser campaigns page
  const { data: placements = [], isLoading, refetch } = useMyPlacements('advertiser')
  const { mutate: updatePlacement, isPending: cancelling, variables: cancellingVars } = useUpdatePlacement()

  const now = new Date()
  const isExpired = (p: { expires_at?: string | null; status: string }) =>
    !!p.expires_at && new Date(p.expires_at) < now && ACTIVE_STATUSES.includes(p.status)

  const activeCnt = placements.filter((p) => getFilter(p.status) === 'active').length
  const completedCnt = placements.filter((p) => getFilter(p.status) === 'completed').length
  const cancelledCnt = placements.filter((p) => getFilter(p.status) === 'cancelled').length

  const filtered = placements.filter((p) => getFilter(p.status) === filter)

  const sorted = [...filtered].sort((a, b) => {
    if (sortKey === 'price') {
      const aP = parseFloat(String(a.final_price ?? a.counter_price ?? a.proposed_price ?? '0'))
      const bP = parseFloat(String(b.final_price ?? b.counter_price ?? b.proposed_price ?? '0'))
      return sortDir === 'asc' ? aP - bP : bP - aP
    }
    // Sort by proposed_schedule (preferred) or created_at as fallback
    const aD = a.proposed_schedule ? new Date(a.proposed_schedule).getTime()
          : a.created_at ? new Date(a.created_at).getTime() : 0
    const bD = b.proposed_schedule ? new Date(b.proposed_schedule).getTime()
          : b.created_at ? new Date(b.created_at).getTime() : 0
    return sortDir === 'asc' ? aD - bD : bD - aD
  })

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
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-display font-bold text-text-primary">Мои кампании</h1>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" onClick={() => void refetch()}>
            🔄
          </Button>
          <Button variant="primary" size="sm" onClick={() => navigate('/adv/campaigns/new/category')}>
            ➕ Создать
          </Button>
        </div>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2 flex-wrap">
        <button
          className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
            filter === 'active'
              ? 'bg-accent-muted text-accent border border-accent/30'
              : 'bg-harbor-card text-text-secondary border border-border hover:border-accent/30'
          }`}
          onClick={() => handleFilterChange('active')}
        >
          🔵 Активные ({activeCnt})
        </button>
        <button
          className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
            filter === 'completed'
              ? 'bg-success-muted text-success border border-success/30'
              : 'bg-harbor-card text-text-secondary border border-border hover:border-success/30'
          }`}
          onClick={() => handleFilterChange('completed')}
        >
          🟢 Завершённые ({completedCnt})
        </button>
        <button
          className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
            filter === 'cancelled'
              ? 'bg-danger-muted text-danger border border-danger/30'
              : 'bg-harbor-card text-text-secondary border border-border hover:border-danger/30'
          }`}
          onClick={() => handleFilterChange('cancelled')}
        >
          🔴 Отменённые ({cancelledCnt})
        </button>
      </div>

      {/* List */}
      {isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-12" />
          <Skeleton className="h-12" />
          <Skeleton className="h-12" />
        </div>
      ) : sorted.length === 0 ? (
        <EmptyState
          icon="📭"
          title="Нет кампаний"
          description={EMPTY_SUBTITLE[filter]}
          action={
            filter === 'active'
              ? { label: '➕ Создать кампанию', onClick: () => navigate('/adv/campaigns/new/category') }
              : undefined
          }
        />
      ) : (
        <>
          {/* Desktop table */}
          <div className="hidden md:block">
            <Card className="p-0 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-harbor-elevated">
                    <tr>
                      <th className="text-left px-4 py-3 text-text-secondary font-medium">Канал</th>
                      <th className="text-left px-4 py-3 text-text-secondary font-medium hidden xl:table-cell">Текст</th>
                      <th
                        className="text-right px-4 py-3 text-text-secondary font-medium cursor-pointer select-none hover:text-text-primary"
                        onClick={() => toggleSort('price')}
                      >
                        Цена <SortIcon active={sortKey === 'price'} dir={sortDir} />
                      </th>
                      <th className="text-left px-4 py-3 text-text-secondary font-medium">Статус</th>
                      <th
                        className="text-right px-4 py-3 text-text-secondary font-medium cursor-pointer select-none hover:text-text-primary"
                        onClick={() => toggleSort('date')}
                        title="Запланированная дата публикации"
                      >
                        Запланировано <SortIcon active={sortKey === 'date'} dir={sortDir} />
                      </th>
                      <th className="text-right px-4 py-3 text-text-secondary font-medium">Действия</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {paged.map((placement) => {
                      const pill = statusToPill(placement.status)
                      const isCancellingThis = cancelling && (cancellingVars as { id?: number } | undefined)?.id === placement.id
                      return (
                        <tr key={placement.id} className="hover:bg-harbor-elevated/50 transition-colors">
                          <td className="px-4 py-3">
                            <p className="font-medium text-text-primary">
                              @{placement.channel?.username ?? `#${placement.channel_id}`}
                            </p>
                            {isExpired(placement) && (
                              <span className="text-xs text-warning">⏰ просрочена</span>
                            )}
                          </td>
                          <td className="px-4 py-3 hidden lg:table-cell max-w-xs">
                            <p className="text-text-secondary truncate text-xs">
                              {placement.ad_text.substring(0, 60)}{placement.ad_text.length > 60 ? '...' : ''}
                            </p>
                          </td>
                          <td className="px-4 py-3 text-right font-mono text-text-primary">
                            {formatCurrency(placement.final_price ?? placement.counter_price ?? placement.proposed_price)}
                          </td>
                          <td className="px-4 py-3">
                            <StatusPill status={pill.status}>{pill.label}</StatusPill>
                          </td>
                          <td className="px-4 py-3 text-right text-text-tertiary text-xs whitespace-nowrap"
                              title={placement.proposed_schedule ? 'Запланированное время' : 'Дата создания'}>
                            {formatSchedule(placement.proposed_schedule) || formatDate(placement.created_at)}
                          </td>
                          <td className="px-4 py-3 text-right">
                            <div className="flex gap-1.5 justify-end">
                              {filter === 'active' && (
                                <>
                                  <Button variant="secondary" size="sm" onClick={() => navigate(`/adv/campaigns/${placement.id}/waiting`)}>
                                    📊
                                  </Button>
                                  <Button
                                    variant="danger"
                                    size="sm"
                                    disabled={isCancellingThis}
                                    onClick={() => {
                                      updatePlacement(
                                        { id: placement.id, data: { action: 'cancel' } },
                                        { onSuccess: () => void refetch() },
                                      )
                                    }}
                                  >
                                    {isCancellingThis ? '⏳' : '❌'}
                                  </Button>
                                </>
                              )}
                              {filter === 'completed' && (
                                <Button variant="secondary" size="sm" onClick={() => navigate(`/adv/campaigns/${placement.id}/published`)}>
                                  📊
                                </Button>
                              )}
                              {filter === 'cancelled' && (
                                <Button variant="ghost" size="sm" onClick={() => navigate(`/adv/campaigns/${placement.id}/waiting`)}>
                                  👁️
                                </Button>
                              )}
                            </div>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>

          {/* Mobile cards */}
          <div className="md:hidden space-y-4">
            {paged.map((placement) => {
              const pill = statusToPill(placement.status)
              const isCancellingThis = cancelling && (cancellingVars as { id?: number } | undefined)?.id === placement.id
              return (
                <Card key={placement.id} className="p-4">
                  {isExpired(placement) && (
                    <Notification type="warning">
                      ⏰ Заявка #{placement.id} просрочена — ожидает автоотмены
                    </Notification>
                  )}
                  <div className="flex items-start justify-between gap-4 mb-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-semibold text-text-primary">
                          #{placement.id} · @{placement.channel?.username ?? `#${placement.channel_id}`}
                        </span>
                        <StatusPill status={pill.status}>{pill.label}</StatusPill>
                      </div>
                      <p className="text-sm text-text-secondary truncate">
                        {placement.ad_text.substring(0, 80)}
                        {placement.ad_text.length > 80 ? '...' : ''}
                      </p>
                      <div className="flex gap-4 mt-2 text-xs text-text-tertiary">
                        <span>{formatCurrency(placement.final_price ?? placement.counter_price ?? placement.proposed_price)}</span>
                        <span title={placement.proposed_schedule ? 'Запланировано' : 'Создана'}>
                          {formatSchedule(placement.proposed_schedule) || formatDate(placement.created_at)}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    {filter === 'active' && (
                      <>
                        <Button variant="secondary" size="sm" icon onClick={() => navigate(`/adv/campaigns/${placement.id}/waiting`)} title="Детали">
                          📊
                        </Button>
                        <Button
                          variant="danger"
                          size="sm"
                          icon
                          disabled={isCancellingThis}
                          onClick={() => {
                            updatePlacement(
                              { id: placement.id, data: { action: 'cancel' } },
                              { onSuccess: () => void refetch() },
                            )
                          }}
                          title="Отменить"
                        >
                          {isCancellingThis ? '⏳' : '❌'}
                        </Button>
                      </>
                    )}
                    {filter === 'completed' && (
                      <Button variant="secondary" size="sm" icon onClick={() => navigate(`/adv/campaigns/${placement.id}/published`)} title="Результат">
                        📊
                      </Button>
                    )}
                    {filter === 'cancelled' && (
                      <Button variant="ghost" size="sm" icon onClick={() => navigate(`/adv/campaigns/${placement.id}/waiting`)} title="Просмотр">
                        👁️
                      </Button>
                    )}
                  </div>
                </Card>
              )
            })}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between">
              <Button size="sm" variant="secondary" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
                ← Назад
              </Button>
              <span className="text-sm text-text-secondary">
                Страница {page + 1} из {totalPages} ({sorted.length} всего)
              </span>
              <Button size="sm" variant="secondary" disabled={page + 1 >= totalPages} onClick={() => setPage((p) => p + 1)}>
                Далее →
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
