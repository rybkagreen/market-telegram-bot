/**
 * AdminDisputeDetail — Dispute detail and resolution screen
 * 
 * Features:
 * - Dispute details display
 * - 4 resolution buttons
 * - Admin comment form
 */

import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useDisputeById, useResolveDispute } from '@/hooks/queries/admin/useAdminQueries'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Card, Button, Notification, Skeleton, StatusPill } from '@/components/ui'
import { formatDateTimeMSK } from '@/lib/constants'
import AdminNav from '@/components/admin/AdminNav'
import styles from './AdminDisputeDetail.module.css'

type Resolution = 'owner_fault' | 'advertiser_fault' | 'technical' | 'partial'

export default function AdminDisputeDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [resolution, setResolution] = useState<Resolution | null>(null)
  const [adminComment, setAdminComment] = useState('')
  const [customSplitPercent, setCustomSplitPercent] = useState(50)

  const { data: dispute, isLoading, error } = useDisputeById(Number(id))
  const resolveMutation = useResolveDispute()

  const handleResolve = () => {
    if (!id || !resolution) return
    if (resolution === 'partial' && (customSplitPercent < 0 || customSplitPercent > 100)) return

    resolveMutation.mutate(
      {
        id: Number(id),
        data: {
          resolution,
          admin_comment: adminComment || undefined,
          custom_split_percent: resolution === 'partial' ? customSplitPercent : undefined,
        },
      },
      {
        onSuccess: () => {
          navigate('/admin/disputes')
        },
      }
    )
  }

  const getResolutionDescription = (res: Resolution) => {
    const descriptions: Record<Resolution, string> = {
      owner_fault: 'Full refund to advertiser (100%), no payout to owner (0%)',
      advertiser_fault: 'No refund to advertiser (0%), full payout to owner (100%)',
      technical: 'Full refund to advertiser (100%), full payout to owner (100%) - platform absorbs loss',
      partial: `Split: advertiser gets ${customSplitPercent}%, owner gets ${100 - customSplitPercent}%`,
    }
    return descriptions[res]
  }

  const getStatusColor = (status: string): 'danger' | 'warning' | 'success' => {
    if (status === 'open') return 'danger'
    if (status === 'owner_explained') return 'warning'
    return 'success'
  }

  if (isLoading) {
    return (
      <ScreenShell>
        <Skeleton height={300} />
      </ScreenShell>
    )
  }

  if (error || !dispute) {
    return (
      <ScreenShell>
        <Notification type="danger">Dispute not found</Notification>
      </ScreenShell>
    )
  }

  return (
    <ScreenShell noPadding className={styles.layout}>
      <aside className={styles.sidebar}>
        <AdminNav />
      </aside>
      <main className={styles.main}>
        <Button variant="secondary" size="sm" onClick={() => navigate('/admin/disputes')} className={styles.backBtn}>
          ← Back to Disputes
        </Button>

        <Card className={styles.card}>
          <h1 className={styles.title}>Dispute #{dispute.id}</h1>

          <div className={styles.meta}>
            <div className={styles.metaItem}>
              <span className={styles.metaLabel}>Status:</span>
              <StatusPill status={getStatusColor(dispute.status)}>{dispute.status}</StatusPill>
            </div>
            <div className={styles.metaItem}>
              <span className={styles.metaLabel}>Reason:</span>
              <span className={styles.metaValue}>{dispute.reason.replace('_', ' ')}</span>
            </div>
            <div className={styles.metaItem}>
              <span className={styles.metaLabel}>Created:</span>
              <span className={styles.metaValue}>
                {formatDateTimeMSK(dispute.created_at)}
              </span>
            </div>
          </div>

          <div className={styles.parties}>
            <div className={styles.party}>
              <h3 className={styles.partyTitle}>Advertiser</h3>
              <p className={styles.partyName}>{dispute.advertiser_username || `User #${dispute.advertiser_id}`}</p>
              {dispute.advertiser_comment && (
                <div className={styles.comment}>
                  <strong>Comment:</strong> {dispute.advertiser_comment}
                </div>
              )}
            </div>

            <div className={styles.party}>
              <h3 className={styles.partyTitle}>Owner</h3>
              <p className={styles.partyName}>{dispute.owner_username || `User #${dispute.owner_id}`}</p>
              {dispute.owner_explanation && (
                <div className={styles.comment}>
                  <strong>Explanation:</strong> {dispute.owner_explanation}
                </div>
              )}
            </div>
          </div>

          {dispute.resolution ? (
            <div className={styles.resolved}>
              <h2 className={styles.sectionTitle}>Resolution</h2>
              <div className={styles.resolutionInfo}>
                <p><strong>Resolution:</strong> {dispute.resolution!.replace('_', ' ')}</p>
                {dispute.resolution_comment && (
                  <p><strong>Comment:</strong> {dispute.resolution_comment}</p>
                )}
                <p><strong>Advertiser Refund:</strong> {dispute.advertiser_refund_pct}%</p>
                <p><strong>Owner Payout:</strong> {dispute.owner_payout_pct}%</p>
                <p><strong>Resolved at:</strong> {formatDateTimeMSK(dispute.resolved_at!)}</p>
              </div>
            </div>
          ) : (
            <div className={styles.resolveSection}>
              <h2 className={styles.sectionTitle}>Resolve Dispute</h2>

              <div className={styles.resolutionButtons}>
                {(['owner_fault', 'advertiser_fault', 'technical', 'partial'] as Resolution[]).map((res) => (
                  <Button
                    key={res}
                    variant={resolution === res ? 'primary' : 'secondary'}
                    onClick={() => setResolution(res)}
                  >
                    {res.replace('_', ' ')}
                  </Button>
                ))}
              </div>

              {resolution && (
                <div className={styles.resolutionDescription}>
                  {getResolutionDescription(resolution)}
                </div>
              )}

              {resolution === 'partial' && (
                <div className={styles.splitControl}>
                  <label className={styles.splitLabel}>
                    Advertiser refund percentage: {customSplitPercent}%
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={customSplitPercent}
                    onChange={(e) => setCustomSplitPercent(Number(e.target.value))}
                    className={styles.slider}
                  />
                  <div className={styles.splitPreview}>
                    <span>Advertiser: {customSplitPercent}%</span>
                    <span>Owner: {100 - customSplitPercent}%</span>
                  </div>
                </div>
              )}

              <div className={styles.commentSection}>
                <label className={styles.commentLabel}>Admin Comment (optional)</label>
                <textarea
                  className={styles.textarea}
                  placeholder="Add a comment explaining your decision..."
                  value={adminComment}
                  onChange={(e) => setAdminComment(e.target.value)}
                  rows={3}
                  maxLength={1024}
                />
              </div>

              <Button
                variant="primary"
                fullWidth
                onClick={handleResolve}
                disabled={!resolution || resolveMutation.isPending}
              >
                {resolveMutation.isPending ? 'Resolving...' : 'Resolve Dispute'}
              </Button>
            </div>
          )}
        </Card>
      </main>
    </ScreenShell>
  )
}
