import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { RequestCard, Button, EmptyState, Skeleton } from '@/components/ui'
import { formatCurrency, formatDate } from '@/lib/formatters'
import { useMyPlacements } from '@/hooks/queries'
import type { PlacementStatus } from '@/lib/types'
import styles from './OwnRequests.module.css'

type Filter = 'new' | 'published' | 'cancelled'
type RequestCardStatus = 'pending_owner' | 'counter_offer' | 'pending_payment' | 'escrow' | 'published' | 'cancelled' | 'refunded' | 'failed'

const NEW_STATUSES: PlacementStatus[] = ['pending_owner', 'counter_offer']
const PUBLISHED_STATUSES: PlacementStatus[] = ['published']
const CANCELLED_STATUSES: PlacementStatus[] = ['cancelled', 'refunded', 'failed', 'failed_permissions']

function toCardStatus(s: string): RequestCardStatus {
  return s === 'failed_permissions' ? 'failed' : (s as RequestCardStatus)
}

export default function OwnRequests() {
  const navigate = useNavigate()
  const [filter, setFilter] = useState<Filter>('new')
  const { data: requests = [], isLoading, refetch } = useMyPlacements({ role: 'owner' })

  const newCount = requests.filter((r) => NEW_STATUSES.includes(r.status as PlacementStatus)).length
  const publishedCount = requests.filter((r) => PUBLISHED_STATUSES.includes(r.status as PlacementStatus)).length
  const cancelledCount = requests.filter((r) => CANCELLED_STATUSES.includes(r.status as PlacementStatus)).length

  const filtered = requests.filter((r) => {
    if (filter === 'new') return NEW_STATUSES.includes(r.status as PlacementStatus)
    if (filter === 'published') return PUBLISHED_STATUSES.includes(r.status as PlacementStatus)
    return CANCELLED_STATUSES.includes(r.status as PlacementStatus)
  })

  return (
    <ScreenShell>
      <div className={styles.toolbar}>
        <div className={styles.filters}>
          <button
            className={`${styles.filterBtn} ${filter === 'new' ? styles.filterDanger : ''}`}
            onClick={() => setFilter('new')}
          >
            🔴 Новые ({newCount})
          </button>
          <button
            className={`${styles.filterBtn} ${filter === 'published' ? styles.filterSuccess : ''}`}
            onClick={() => setFilter('published')}
          >
            🟢 ({publishedCount})
          </button>
          <button
            className={`${styles.filterBtn} ${filter === 'cancelled' ? styles.filterNeutral : ''}`}
            onClick={() => setFilter('cancelled')}
          >
            ⬜ ({cancelledCount})
          </button>
        </div>
        <Button variant="secondary" size="sm" onClick={() => refetch()}>🔄</Button>
      </div>

      {isLoading ? (
        <div className={styles.list}>
          <Skeleton height={90} />
          <Skeleton height={90} />
          <Skeleton height={90} />
        </div>
      ) : (
        <div className={styles.list}>
          {filtered.length === 0 && (
            <EmptyState icon="📋" title="Нет заявок" description="В этом разделе пусто" />
          )}

          {filtered.map((req) => (
            <div key={req.id} className={styles.item}>
              <RequestCard
                id={req.id}
                channelName={req.channel ? `@${req.channel.username}` : `#${req.channel_id}`}
                adText={req.ad_text}
                price={formatCurrency(req.proposed_price)}
                date={formatDate(req.created_at)}
                status={toCardStatus(req.status)}
                isOwner
                onClick={() => navigate(`/own/requests/${req.id}`)}
              />

              <div className={styles.actions}>
                {(req.status === 'pending_owner' || req.status === 'counter_offer') && (
                  <>
                    <Button size="sm" variant="success" onClick={() => navigate(`/own/requests/${req.id}`)}>
                      ✅ Принять
                    </Button>
                    <Button size="sm" variant="danger" onClick={() => navigate(`/own/requests/${req.id}`)}>
                      ❌ Отклонить
                    </Button>
                    <Button size="sm" variant="secondary" onClick={() => navigate(`/own/requests/${req.id}`)}>
                      ✏️
                    </Button>
                  </>
                )}
                {req.status === 'published' && (
                  <>
                    <Button size="sm" variant="secondary" onClick={() => navigate(`/own/requests/${req.id}`)}>
                      📊 Детали
                    </Button>
                    <Button size="sm" variant="success" onClick={() => navigate(`/own/requests/${req.id}`, { state: { openReview: true } })}>
                      ⭐ Отзыв
                    </Button>
                  </>
                )}
                {(req.status === 'cancelled' || req.status === 'refunded' || req.status === 'failed') && (
                  <Button size="sm" variant="secondary" onClick={() => navigate(`/own/requests/${req.id}`)}>
                    📊 Детали
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </ScreenShell>
  )
}
