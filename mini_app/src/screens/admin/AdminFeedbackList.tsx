/**
 * AdminFeedbackList — List of all user feedback
 * 
 * Features:
 * - Feedback table with pagination
 * - Status filter
 * - View details button
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useFeedbackList } from '@/hooks/queries/admin/useAdminQueries'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Card, Button, Skeleton, Notification, StatusPill } from '@/components/ui'
import { formatDateMSK } from '@/lib/constants'
import AdminNav from '@/components/admin/AdminNav'
import styles from './AdminFeedbackList.module.css'

type StatusFilter = 'all' | 'new' | 'in_progress' | 'resolved' | 'rejected'

const statusColors: Record<string, 'info' | 'warning' | 'success' | 'danger'> = {
  new: 'info',
  in_progress: 'warning',
  resolved: 'success',
  rejected: 'danger',
}

export default function AdminFeedbackList() {
  const navigate = useNavigate()
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [page, setPage] = useState(0)
  const limit = 20

  const { data, isLoading, error } = useFeedbackList({
    status: statusFilter,
    limit,
    offset: page * limit,
  })

  const handleRowClick = (id: number) => {
    navigate(`/admin/feedback/${id}`)
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
        <Notification type="danger">Failed to load feedback</Notification>
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
          <h1 className={styles.title}>Feedback</h1>
          
          <div className={styles.filters}>
            {(['all', 'new', 'in_progress', 'resolved', 'rejected'] as StatusFilter[]).map((status) => (
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
              <div className={styles.empty}>No feedback found</div>
            </Card>
          ) : (
            data.items.map((feedback) => (
              <Card 
                key={feedback.id}
                className={styles.feedbackCard}
                onClick={() => handleRowClick(feedback.id)}
              >
                <div className={styles.feedbackHeader}>
                  <div className={styles.feedbackMeta}>
                    <span className={styles.feedbackId}>#{feedback.id}</span>
                    <span className={styles.feedbackUser}>
                      {feedback.username || `User #${feedback.user_id}`}
                    </span>
                  </div>
                  <StatusPill status={statusColors[feedback.status] || 'blue'}>
                    {feedback.status}
                  </StatusPill>
                </div>
                <p className={styles.feedbackText}>{feedback.text}</p>
                <div className={styles.feedbackFooter}>
                  <span className={styles.feedbackDate}>
                    {formatDateMSK(feedback.created_at)}
                  </span>
                  <Button size="sm" variant="secondary">View</Button>
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
