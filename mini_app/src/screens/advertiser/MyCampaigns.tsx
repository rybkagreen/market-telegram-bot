import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { RequestCard, EmptyState, Button, StatusPill, Skeleton, Notification } from '@/components/ui'
import { formatCurrency, formatDate } from '@/lib/formatters'
import { useMyPlacements, useUpdatePlacement } from '@/hooks/queries'
import type { PlacementStatus } from '@/lib/types'
import styles from './MyCampaigns.module.css'

type Filter = 'active' | 'completed' | 'cancelled'

const ACTIVE_STATUSES: PlacementStatus[] = ['pending_owner', 'counter_offer', 'pending_payment', 'escrow']
const COMPLETED_STATUSES: PlacementStatus[] = ['published']
const CANCELLED_STATUSES: PlacementStatus[] = ['cancelled', 'refunded', 'failed', 'failed_permissions']

function getFilter(status: PlacementStatus): Filter {
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

export default function MyCampaigns() {
  const navigate = useNavigate()
  const [filter, setFilter] = useState<Filter>('active')
  const { data: placements = [], isLoading, refetch } = useMyPlacements()
  const { mutate: updatePlacement, isPending: cancelling, variables: cancellingVars } = useUpdatePlacement()

  const now = new Date()
  const isExpired = (p: { expires_at?: string | null; status: PlacementStatus }) =>
    !!p.expires_at && new Date(p.expires_at) < now && ACTIVE_STATUSES.includes(p.status)

  const activeCnt = placements.filter((p) => getFilter(p.status) === 'active').length
  const completedCnt = placements.filter((p) => getFilter(p.status) === 'completed').length
  const cancelledCnt = placements.filter((p) => getFilter(p.status) === 'cancelled').length

  const filtered = placements.filter((p) => getFilter(p.status) === filter)

  return (
    <ScreenShell>
      <div className={styles.toolbar}>
        <Button variant="secondary" size="sm" onClick={() => { void refetch() }}>
          🔄 Обновить
        </Button>
      </div>

      <div className={styles.tabs}>
        <button
          className={`${styles.tab} ${filter === 'active' ? styles.active : ''}`}
          onClick={() => setFilter('active')}
        >
          <StatusPill status="info" size="sm">🔵 Активные ({activeCnt})</StatusPill>
        </button>
        <button
          className={`${styles.tab} ${filter === 'completed' ? styles.active : ''}`}
          onClick={() => setFilter('completed')}
        >
          <StatusPill status="success" size="sm">🟢 Завершённые ({completedCnt})</StatusPill>
        </button>
        <button
          className={`${styles.tab} ${filter === 'cancelled' ? styles.active : ''}`}
          onClick={() => setFilter('cancelled')}
        >
          <StatusPill status="danger" size="sm">🔴 Отменённые ({cancelledCnt})</StatusPill>
        </button>
      </div>

      {isLoading ? (
        <div className={styles.list}>
          <Skeleton height={90} />
          <Skeleton height={90} />
          <Skeleton height={90} />
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          icon="📭"
          title="Нет кампаний"
          description={EMPTY_SUBTITLE[filter]}
          action={filter === 'active'
            ? { label: '➕ Создать кампанию', onClick: () => { navigate('/adv/campaigns/new/category') } }
            : undefined
          }
        />
      ) : (
        <div className={styles.list}>
          {filtered.map((placement) => (
            <div key={placement.id} className={styles.item}>
              {isExpired(placement) && (
                <Notification type="warning">
                  ⏰ Заявка #{placement.id} просрочена — ожидает автоотмены
                </Notification>
              )}
              <RequestCard
                id={placement.id}
                channelName={placement.channel ? `@${placement.channel.username}` : `#${placement.channel_id}`}
                adText={placement.ad_text}
                price={formatCurrency(placement.final_price ?? placement.proposed_price)}
                date={formatDate(placement.created_at)}
                status={placement.status === 'failed_permissions' ? 'failed' : placement.status}
                onClick={() => {
                  if (filter === 'active') navigate(`/adv/campaigns/${placement.id}/waiting`)
                  else alert(`Детали кампании #${placement.id} — Phase 8`)
                }}
              />
              <div className={styles.actions}>
                <Button variant="secondary" size="sm" onClick={() => navigate(`/adv/campaigns/${placement.id}/waiting`)}>
                  📊 Детали
                </Button>
                {filter === 'active' && (
                  <Button
                    variant="danger"
                    size="sm"
                    disabled={cancelling && cancellingVars?.id === placement.id}
                    onClick={() => {
                      updatePlacement(
                        { id: placement.id, data: { action: 'cancel' } },
                        { onSuccess: () => { void refetch() } },
                      )
                    }}
                  >
                    {cancelling && cancellingVars?.id === placement.id ? '⏳...' : '❌ Отменить'}
                  </Button>
                )}
                {filter === 'completed' && (
                  <Button variant="success" size="sm" onClick={() => alert(`Отзыв #${placement.id}`)}>
                    ⭐ Отзыв
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
