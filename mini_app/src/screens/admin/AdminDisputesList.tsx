/**
 * AdminDisputesList — List of all disputes
 * 
 * Features:
 * - Disputes table with pagination
 * - Status filter
 * - Urgency indicators
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDisputesList } from '@/hooks/queries/admin/useAdminQueries'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Card, Button, Skeleton, Notification, StatusPill } from '@/components/ui'
import AdminNav from '@/components/admin/AdminNav'
import styles from './AdminDisputesList.module.css'

type StatusFilter = 'all' | 'open' | 'owner_explained' | 'resolved'

const statusColors: Record<string, 'danger' | 'warning' | 'success'> = {
  open: 'danger',
  owner_explained: 'warning',
  resolved: 'success',
}

const reasonEmoji: Record<string, string> = {
  post_removed_early: '🗑️',
  bot_kicked: '🤖',
  advertiser_complaint: '📢',
}

export default function AdminDisputesList() {
  const navigate = useNavigate()
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('open')
  const [page, setPage] = useState(0)
  const limit = 20

  const { data, isLoading, error } = useDisputesList({
    status: statusFilter,
    limit,
    offset: page * limit,
  })

  const handleRowClick = (id: number) => {
    navigate(`/admin/disputes/${id}`)
  }

  if (isLoading) {
    return (
      <ScreenShell>
        <Skeleton height={300} />
      </ScreenShell>
    )
  }

  if (error || !data) {
    return (
      <ScreenShell>
        <Notification type="danger">Failed to load disputes</Notification>
      </ScreenShell>
    )
  }

  return (
    <ScreenShell noPadding className={styles.layout}>
      <aside className={styles.sidebar}>
        <AdminNav />
      </aside>
      <main className={styles.main}>
        <div className={styles.header}>
          <h1 className={styles.title}>Disputes</h1>
          
          <div className={styles.filters}>
            {(['all', 'open', 'owner_explained', 'resolved'] as StatusFilter[]).map((status) => (
              <button
                key={status}
                className={`${styles.filterBtn} ${statusFilter === status ? styles.active : ''}`}
                onClick={() => {
                  setStatusFilter(status)
                  setPage(0)
                }}
              >
                {status === 'all' ? 'All' : status.replace('_', ' ')}
              </button>
            ))}
          </div>
        </div>

        <div className={styles.list}>
          {data.items.length === 0 ? (
            <Card>
              <div className={styles.empty}>No disputes found</div>
            </Card>
          ) : (
            data.items.map((dispute) => (
              <Card 
                key={dispute.id}
                className={styles.disputeCard}
                onClick={() => handleRowClick(dispute.id)}
              >
                <div className={styles.disputeHeader}>
                  <div className={styles.disputeMeta}>
                    <span className={styles.disputeId}>#{dispute.id}</span>
                    <span className={styles.disputeReason}>
                      {reasonEmoji[dispute.reason] || '⚠️'} {dispute.reason.replace('_', ' ')}
                    </span>
                  </div>
                  <StatusPill status={statusColors[dispute.status] || 'blue'}>
                    {dispute.status}
                  </StatusPill>
                </div>
                <div className={styles.disputeParties}>
                  <span className={styles.party}>
                    <strong>Advertiser:</strong> {dispute.advertiser_username || `User #${dispute.advertiser_id}`}
                  </span>
                  <span className={styles.party}>
                    <strong>Owner:</strong> {dispute.owner_username || `User #${dispute.owner_id}`}
                  </span>
                </div>
                <div className={styles.disputeFooter}>
                  <span className={styles.disputeDate}>
                    {new Date(dispute.created_at).toLocaleDateString()}
                  </span>
                  <Button size="sm" variant={dispute.status === 'resolved' ? 'secondary' : 'primary'}>
                    {dispute.status === 'resolved' ? 'View' : 'Resolve'}
                  </Button>
                </div>
              </Card>
            ))
          )}
        </div>

        {/* Pagination */}
        {data.total > limit && (
          <div className={styles.pagination}>
            <Button
              size="sm"
              variant="secondary"
              disabled={page === 0}
              onClick={() => setPage(page - 1)}
            >
              Previous
            </Button>
            <span className={styles.pageInfo}>
              Page {page + 1} of {Math.ceil(data.total / limit)}
            </span>
            <Button
              size="sm"
              variant="secondary"
              disabled={(page + 1) * limit >= data.total}
              onClick={() => setPage(page + 1)}
            >
              Next
            </Button>
          </div>
        )}
      </main>
    </ScreenShell>
  )
}
