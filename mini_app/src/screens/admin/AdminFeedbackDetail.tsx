/**
 * AdminFeedbackDetail — Feedback detail and response screen
 * 
 * Features:
 * - Feedback details display
 * - Response form
 * - Status change buttons
 */

import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { 
  useFeedbackById, 
  useRespondToFeedback, 
  useUpdateFeedbackStatus 
} from '@/hooks/queries/admin/useAdminQueries'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Card, Button, Notification, Skeleton } from '@/components/ui'
import { formatDateTimeMSK } from '@/lib/constants'
import AdminNav from '@/components/admin/AdminNav'
import styles from './AdminFeedbackDetail.module.css'

export default function AdminFeedbackDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [responseText, setResponseText] = useState('')
  const [responseStatus, setResponseStatus] = useState<'in_progress' | 'resolved' | 'rejected'>('resolved')

  const { data: feedback, isLoading, error } = useFeedbackById(Number(id))
  const respondMutation = useRespondToFeedback()
  const statusMutation = useUpdateFeedbackStatus()

  const handleRespond = () => {
    if (!id || responseText.length < 10) return
    
    respondMutation.mutate(
      { id: Number(id), data: { response_text: responseText, status: responseStatus } },
      {
        onSuccess: () => {
          setResponseText('')
          navigate('/admin/feedback')
        },
      }
    )
  }

  const handleStatusChange = (status: 'new' | 'in_progress' | 'resolved' | 'rejected') => {
    if (!id) return
    statusMutation.mutate({ id: Number(id), data: { status } })
  }

  if (isLoading) {
    return (
      <ScreenShell>
        <Skeleton height={300} />
      </ScreenShell>
    )
  }

  if (error || !feedback) {
    return (
      <ScreenShell>
        <Notification type="danger">Feedback not found</Notification>
      </ScreenShell>
    )
  }

  return (
    <ScreenShell noPadding className={styles.layout}>
      <aside className={styles.sidebar}>
        <AdminNav />
      </aside>
      <main className={styles.main}>
        <Button variant="secondary" size="sm" onClick={() => navigate('/admin/feedback')} className={styles.backBtn}>
          ← Back to Feedback
        </Button>

        <Card className={styles.card}>
          <h1 className={styles.title}>Feedback #{feedback.id}</h1>

          <div className={styles.meta}>
            <div className={styles.metaItem}>
              <span className={styles.metaLabel}>User:</span>
              <span className={styles.metaValue}>
                {feedback.username || `User #${feedback.user_id}`}
              </span>
            </div>
            <div className={styles.metaItem}>
              <span className={styles.metaLabel}>Status:</span>
              <span className={feedback.status === 'resolved' ? styles.statusResolved : feedback.status === 'rejected' ? styles.statusRejected : feedback.status === 'in_progress' ? styles.statusInProgress : styles.statusNew}>
                {feedback.status}
              </span>
            </div>
            <div className={styles.metaItem}>
              <span className={styles.metaLabel}>Created:</span>
              <span className={styles.metaValue}>
                {formatDateTimeMSK(feedback.created_at)}
              </span>
            </div>
          </div>

          <div className={styles.section}>
            <h2 className={styles.sectionTitle}>Message</h2>
            <div className={styles.message}>{feedback.text}</div>
          </div>

          {feedback.admin_response && (
            <div className={styles.section}>
              <h2 className={styles.sectionTitle}>Admin Response</h2>
              <div className={styles.response}>
                <p className={styles.responseText}>{feedback.admin_response}</p>
                {feedback.responded_at && (
                  <p className={styles.respondedAt}>
                    Responded: {formatDateTimeMSK(feedback.responded_at)}
                  </p>
                )}
              </div>
            </div>
          )}

          <div className={styles.section}>
            <h2 className={styles.sectionTitle}>Change Status</h2>
            <div className={styles.statusButtons}>
              {(['new', 'in_progress', 'resolved', 'rejected'] as const).map((status) => (
                <Button
                  key={status}
                  variant={feedback.status === status ? 'primary' : 'secondary'}
                  size="sm"
                  onClick={() => handleStatusChange(status)}
                  disabled={statusMutation.isPending}
                >
                  {status}
                </Button>
              ))}
            </div>
          </div>

          {!feedback.admin_response && (
            <div className={styles.section}>
              <h2 className={styles.sectionTitle}>Send Response</h2>
              <textarea
                className={styles.textarea}
                placeholder="Type your response here (min 10 characters)..."
                value={responseText}
                onChange={(e) => setResponseText(e.target.value)}
                rows={5}
                minLength={10}
                maxLength={2048}
              />
              <div className={styles.responseOptions}>
                <select
                  className={styles.select}
                  value={responseStatus}
                  onChange={(e) => setResponseStatus(e.target.value as typeof responseStatus)}
                >
                  <option value="resolved">Mark as Resolved</option>
                  <option value="in_progress">Mark as In Progress</option>
                  <option value="rejected">Mark as Rejected</option>
                </select>
                <Button
                  variant="primary"
                  onClick={handleRespond}
                  disabled={responseText.length < 10 || respondMutation.isPending}
                >
                  {respondMutation.isPending ? 'Sending...' : 'Send Response'}
                </Button>
              </div>
            </div>
          )}
        </Card>
      </main>
    </ScreenShell>
  )
}
