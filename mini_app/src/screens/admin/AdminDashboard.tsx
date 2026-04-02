/**
 * AdminDashboard — Main admin dashboard screen
 * 
 * Features:
 * - Platform statistics cards
 * - Quick actions
 * - Recent activity overview
 */

import { useNavigate } from 'react-router-dom'
import * as Sentry from '@sentry/react'
import { usePlatformStats } from '@/hooks/queries/admin/useAdminQueries'
import { useMe } from '@/hooks/queries'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Card, Skeleton, Notification, MenuButton } from '@/components/ui'
import AdminNav from '@/components/admin/AdminNav'
import styles from './AdminDashboard.module.css'

export default function AdminDashboard() {
  const navigate = useNavigate()
  const { data: user, isLoading: userLoading } = useMe()
  const { data: stats, isLoading, error } = usePlatformStats()

  // Check admin access
  if (userLoading) {
    return (
      <ScreenShell>
        <Skeleton height={200} />
      </ScreenShell>
    )
  }

  if (!user?.is_admin) {
    return (
      <ScreenShell>
        <Notification type="danger">
          Доступ запрещён. Требуется роль администратора.
        </Notification>
        <MenuButton
          variant="back"
          icon="🔙"
          title="В главное меню"
          onClick={() => navigate('/')}
        />
      </ScreenShell>
    )
  }

  if (isLoading) {
    return (
      <ScreenShell>
        <div className={styles.loading}>
          <Skeleton height={200} />
        </div>
      </ScreenShell>
    )
  }

  if (error || !stats) {
    if (error) Sentry.captureException(error)
    return (
      <ScreenShell>
        <Notification type="danger">
          Failed to load statistics
          {error && <div style={{ fontSize: '12px', marginTop: '8px' }}>Error: {error.message}</div>}
        </Notification>
      </ScreenShell>
    )
  }

  return (
    <ScreenShell noPadding className={styles.layout}>
      <aside className={styles.sidebar}>
        <AdminNav />
      </aside>
      <main className={styles.main}>
        <h1 className={styles.title}>Dashboard</h1>
        
        <div className={styles.statsGrid}>
          {/* Users Stats */}
          <Card title="👥 Users">
            <div className={styles.statValue}>{stats.users.total}</div>
            <div className={styles.statDetails}>
              <span>Active: {stats.users.active}</span>
              <span>Admins: {stats.users.admins}</span>
            </div>
          </Card>

          {/* Feedback Stats */}
          <Card title="💬 Feedback">
            <div className={styles.statValue}>{stats.feedback.total}</div>
            <div className={styles.statDetails}>
              <span>New: {stats.feedback.new}</span>
              <span>Resolved: {stats.feedback.resolved}</span>
            </div>
          </Card>

          {/* Disputes Stats */}
          <Card title="⚖️ Disputes">
            <div className={styles.statValue}>{stats.disputes.total}</div>
            <div className={styles.statDetails}>
              <span>Open: {stats.disputes.open}</span>
              <span>Resolved: {stats.disputes.resolved}</span>
            </div>
          </Card>

          {/* Placements Stats */}
          <Card title="📍 Placements">
            <div className={styles.statValue}>{stats.placements.total}</div>
            <div className={styles.statDetails}>
              <span>Active: {stats.placements.active}</span>
              <span>Completed: {stats.placements.completed}</span>
            </div>
          </Card>

          {/* Financial Stats */}
          <Card title="💰 Financial">
            <div className={styles.statValue}>{stats.financial.total_revenue} ₽</div>
            <div className={styles.statDetails}>
              <span>Payouts: {stats.financial.total_payouts} ₽</span>
              <span>Pending: {stats.financial.pending_payouts} ₽</span>
            </div>
          </Card>
        </div>

        {/* Back to Main Menu Button */}
        <div style={{ marginTop: 'var(--rh-space-6)' }}>
          <MenuButton
            variant="back"
            icon="🔙"
            title="В главное меню"
            onClick={() => navigate('/')}
          />
        </div>
      </main>
    </ScreenShell>
  )
}
