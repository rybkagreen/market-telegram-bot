import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button, StatusPill, Skeleton, EmptyState, Card } from '@shared/ui'
import { formatCurrency, formatDateMSK, formatDateTimeMSK } from '@/lib/constants'
import { useMyPlacements } from '@/hooks/useCampaignQueries'

type Filter = 'new' | 'active' | 'cancelled'
type SortKey = 'date' | 'price'
type SortDir = 'asc' | 'desc'

const NEW_STATUSES = ['pending_owner', 'counter_offer', 'pending_payment']
const ACTIVE_STATUSES = ['escrow', 'published']
const CANCELLED_STATUSES = ['cancelled', 'refunded', 'failed', 'failed_permissions']
const PAGE_SIZE = 10

function getFilter(status: string): Filter {
  if (NEW_STATUSES.includes(status)) return 'new'
  if (ACTIVE_STATUSES.includes(status)) return 'active'
  if (CANCELLED_STATUSES.includes(status)) return 'cancelled'
  return 'cancelled'
}

const EMPTY_SUBTITLE: Record<Filter, string> = {
  new: 'Нет новых заявок — они появятся, когда рекламодатели отправят запросы',
  active: 'Нет активных размещений',
  cancelled: 'Нет отменённых заявок',
}

function formatDate(dt: string | null | undefined): string {
  return formatDateMSK(dt)
}

function formatSchedule(dt: string | null | undefined): string {
  return formatDateTimeMSK(dt)
}

function statusToPill(status: string): { status: 'success' | 'warning' | 'danger' | 'default'; label: string } {
  const map: Record<string, { status: 'success' | 'warning' | 'danger' | 'default'; label: string }> = {
    pending_owner: { status: 'warning', label: '⏳ Новая заявка' },
    counter_offer: { status: 'warning', label: '🔄 Контр-оферта' },
    pending_payment: { status: 'warning', label: '💳 Ожидает оплаты' },
    escrow: { status: 'success', label: '🔒 В эскроу' },
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

export default function OwnRequests() {
  const navigate = useNavigate()
  const [filter, setFilter] = useState<Filter>('new')
  const [sortKey, setSortKey] = useState<SortKey>('date')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [page, setPage] = useState(0)
  const { data: requests = [], isLoading, refetch } = useMyPlacements('owner')

  const newCount = requests.filter((r) => getFilter(r.status) === 'new').length
  const activeCount = requests.filter((r) => getFilter(r.status) === 'active').length
  const cancelledCount = requests.filter((r) => getFilter(r.status) === 'cancelled').length

  const filtered = requests.filter((r) => getFilter(r.status) === filter)

  const sorted = [...filtered].sort((a, b) => {
    if (sortKey === 'price') {
      const aP = parseFloat(String(a.final_price ?? a.proposed_price ?? '0'))
      const bP = parseFloat(String(b.final_price ?? b.proposed_price ?? '0'))
      return sortDir === 'asc' ? aP - bP : bP - aP
    }
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
        <h1 className="text-2xl font-display font-bold text-text-primary">Входящие заявки</h1>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" onClick={() => void refetch()}>
            🔄
          </Button>
        </div>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2 flex-wrap">
        <button
          className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
            filter === 'new'
              ? 'bg-warning-muted text-warning border border-warning/30'
              : 'bg-harbor-card text-text-secondary border border-border hover:border-warning/30'
          }`}
          onClick={() => handleFilterChange('new')}
        >
          🟡 Новые ({newCount})
        </button>
        <button
          className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
            filter === 'active'
              ? 'bg-success-muted text-success border border-success/30'
              : 'bg-harbor-card text-text-secondary border border-border hover:border-success/30'
          }`}
          onClick={() => handleFilterChange('active')}
        >
          🟢 Активные ({activeCount})
        </button>
        <button
          className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
            filter === 'cancelled'
              ? 'bg-danger-muted text-danger border border-danger/30'
              : 'bg-harbor-card text-text-secondary border border-border hover:border-danger/30'
          }`}
          onClick={() => handleFilterChange('cancelled')}
        >
          🔴 Отменённые ({cancelledCount})
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
          icon="📋"
          title="Нет заявок"
          description={EMPTY_SUBTITLE[filter]}
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
                    {paged.map((req) => {
                      const pill = statusToPill(req.status)
                      const isActionable = ['pending_owner', 'counter_offer'].includes(req.status)
                      return (
                        <tr key={req.id} className="hover:bg-harbor-elevated/50 transition-colors">
                          <td className="px-4 py-3">
                            <p className="font-medium text-text-primary">
                              @{req.channel?.username ?? `#${req.channel_id}`}
                            </p>
                          </td>
                          <td className="px-4 py-3 hidden xl:table-cell max-w-xs">
                            <p className="text-text-secondary truncate text-xs">
                              {req.ad_text.substring(0, 60)}{req.ad_text.length > 60 ? '...' : ''}
                            </p>
                          </td>
                          <td className="px-4 py-3 text-right font-mono text-text-primary">
                            {formatCurrency(req.final_price ?? req.proposed_price)}
                          </td>
                          <td className="px-4 py-3">
                            <StatusPill status={pill.status}>{pill.label}</StatusPill>
                          </td>
                          <td className="px-4 py-3 text-right text-text-tertiary text-xs whitespace-nowrap"
                              title={req.proposed_schedule ? 'Запланированное время' : 'Дата создания'}>
                            {formatSchedule(req.proposed_schedule) || formatDate(req.created_at)}
                          </td>
                          <td className="px-4 py-3 text-right">
                            <div className="flex gap-1.5 justify-end">
                              {isActionable && (
                                <>
                                  <Button variant="success" size="sm" onClick={() => navigate(`/own/requests/${req.id}`)}>
                                    ✅
                                  </Button>
                                  <Button variant="secondary" size="sm" onClick={() => navigate(`/own/requests/${req.id}`)}>
                                    ✏️
                                  </Button>
                                  <Button variant="danger" size="sm" onClick={() => navigate(`/own/requests/${req.id}`)}>
                                    ❌
                                  </Button>
                                </>
                              )}
                              {ACTIVE_STATUSES.includes(req.status) && (
                                <Button variant="secondary" size="sm" onClick={() => navigate(`/own/requests/${req.id}`)}>
                                  📊
                                </Button>
                              )}
                              {CANCELLED_STATUSES.includes(req.status) && (
                                <Button variant="ghost" size="sm" onClick={() => navigate(`/own/requests/${req.id}`)}>
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
            {paged.map((req) => {
              const pill = statusToPill(req.status)
              const isActionable = ['pending_owner', 'counter_offer'].includes(req.status)

              return (
                <Card key={req.id} className="p-4">
                  <div className="flex items-start justify-between gap-4 mb-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-semibold text-text-primary">
                          #{req.id} · @{req.channel?.username ?? `#${req.channel_id}`}
                        </span>
                        <StatusPill status={pill.status}>{pill.label}</StatusPill>
                      </div>
                      <p className="text-sm text-text-secondary truncate">
                        {req.ad_text.substring(0, 80)}
                        {req.ad_text.length > 80 ? '...' : ''}
                      </p>
                      <div className="flex gap-4 mt-2 text-xs text-text-tertiary">
                        <span>{formatCurrency(req.final_price ?? req.proposed_price)}</span>
                        <span title={req.proposed_schedule ? 'Запланировано' : 'Создана'}>
                          {formatSchedule(req.proposed_schedule) || formatDate(req.created_at)}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="flex gap-2 flex-wrap">
                    {isActionable && (
                      <>
                        <Button variant="success" size="sm" onClick={() => navigate(`/own/requests/${req.id}`)}>
                          ✅ Принять
                        </Button>
                        <Button variant="secondary" size="sm" onClick={() => navigate(`/own/requests/${req.id}`)}>
                          ✏️ Контр-оферта
                        </Button>
                        <Button variant="danger" size="sm" onClick={() => navigate(`/own/requests/${req.id}`)}>
                          ❌ Отклонить
                        </Button>
                      </>
                    )}
                    {ACTIVE_STATUSES.includes(req.status) && (
                      <Button variant="secondary" size="sm" onClick={() => navigate(`/own/requests/${req.id}`)}>
                        📊 Детали
                      </Button>
                    )}
                    {CANCELLED_STATUSES.includes(req.status) && (
                      <Button variant="ghost" size="sm" onClick={() => navigate(`/own/requests/${req.id}`)}>
                        👁️ Просмотр
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
