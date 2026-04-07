import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button, StatusPill, Skeleton, EmptyState, Card } from '@shared/ui'
import { formatCurrency } from '@/lib/constants'
import { useMyPlacements } from '@/hooks/useCampaignQueries'

type Filter = 'new' | 'published' | 'cancelled'

const NEW_STATUSES = ['pending_owner', 'counter_offer']
const PUBLISHED_STATUSES = ['published']
const CANCELLED_STATUSES = ['cancelled', 'refunded', 'failed', 'failed_permissions']

function formatDate(dt: string | null | undefined): string {
  if (!dt) return '—'
  return new Date(dt).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

function statusToPill(status: string): { status: 'success' | 'warning' | 'danger' | 'default'; label: string } {
  const map: Record<string, { status: 'success' | 'warning' | 'danger' | 'default'; label: string }> = {
    pending_owner: { status: 'warning', label: '⏳ Новая заявка' },
    counter_offer: { status: 'warning', label: '🔄 Контр-оферта' },
    published: { status: 'success', label: '✅ Опубликован' },
    cancelled: { status: 'danger', label: '❌ Отменён' },
    refunded: { status: 'danger', label: '💸 Возврат' },
    failed: { status: 'danger', label: '⚠️ Ошибка' },
    failed_permissions: { status: 'danger', label: '⚠️ Нет прав' },
  }
  return map[status] ?? { status: 'default', label: status }
}

export default function OwnRequests() {
  const navigate = useNavigate()
  const [filter, setFilter] = useState<Filter>('new')
  const { data: requests = [], isLoading, refetch } = useMyPlacements(undefined, 'owner')

  const newCount = requests.filter((r) => NEW_STATUSES.includes(r.status)).length
  const publishedCount = requests.filter((r) => PUBLISHED_STATUSES.includes(r.status)).length
  const cancelledCount = requests.filter((r) => CANCELLED_STATUSES.includes(r.status)).length

  const filtered = requests.filter((r) => {
    if (filter === 'new') return NEW_STATUSES.includes(r.status)
    if (filter === 'published') return PUBLISHED_STATUSES.includes(r.status)
    return CANCELLED_STATUSES.includes(r.status)
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-display font-bold text-text-primary">Входящие заявки</h1>
        <Button variant="secondary" size="sm" onClick={() => void refetch()}>🔄</Button>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2 flex-wrap">
        <button
          className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
            filter === 'new'
              ? 'bg-danger-muted text-danger border border-danger/30'
              : 'bg-harbor-card text-text-secondary border border-border hover:border-danger/30'
          }`}
          onClick={() => setFilter('new')}
        >
          🔴 Новые ({newCount})
        </button>
        <button
          className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
            filter === 'published'
              ? 'bg-success-muted text-success border border-success/30'
              : 'bg-harbor-card text-text-secondary border border-border hover:border-success/30'
          }`}
          onClick={() => setFilter('published')}
        >
          🟢 Опубли. ({publishedCount})
        </button>
        <button
          className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
            filter === 'cancelled'
              ? 'bg-harbor-elevated text-text-secondary border border-border'
              : 'bg-harbor-card text-text-secondary border border-border hover:border-accent/30'
          }`}
          onClick={() => setFilter('cancelled')}
        >
          ⬜ Отмен. ({cancelledCount})
        </button>
      </div>

      {/* List */}
      {isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState icon="📋" title="Нет заявок" description="В этом разделе пусто" />
      ) : (
        <div className="space-y-4">
          {filtered.map((req) => {
            const pill = statusToPill(req.status)
            const isNew = NEW_STATUSES.includes(req.status)

            return (
              <Card key={req.id} className="p-4">
                <div className="flex items-start gap-3 mb-3">
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
                      <span>{formatCurrency(req.proposed_price)}</span>
                      <span>{formatDate(req.created_at)}</span>
                    </div>
                  </div>
                </div>

                <div className="flex gap-2 flex-wrap">
                  {isNew && (
                    <>
                      <Button variant="success" size="sm" onClick={() => navigate(`/own/requests/${req.id}`)}>
                        ✅ Принять
                      </Button>
                      <Button variant="danger" size="sm" onClick={() => navigate(`/own/requests/${req.id}`)}>
                        ❌ Отклонить
                      </Button>
                      <Button variant="secondary" size="sm" onClick={() => navigate(`/own/requests/${req.id}`)}>
                        ✏️ Контр-оферта
                      </Button>
                    </>
                  )}
                  {req.status === 'published' && (
                    <>
                      <Button variant="secondary" size="sm" onClick={() => navigate(`/own/requests/${req.id}`)}>
                        📊 Детали
                      </Button>
                      <Button variant="success" size="sm" onClick={() => navigate(`/own/requests/${req.id}`)}>
                        ⭐ Отзыв
                      </Button>
                    </>
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
      )}
    </div>
  )
}
