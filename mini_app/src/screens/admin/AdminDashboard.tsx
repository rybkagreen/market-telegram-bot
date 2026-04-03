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

function formatRub(value: string | number): string {
  const num = typeof value === 'string' ? parseFloat(value) : value
  return num.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' ₽'
}

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
          {error && <div className={styles.errorDetail}>Error: {error.message}</div>}
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
          <Card title="💰 Балансы платформы">
            <div className={styles.finGrid}>
              <div className={styles.finRow}>
                <span className={styles.finLabel}>💳 Внесено всего</span>
                <span className={styles.finValueIn}>{formatRub(stats.financial.total_topups)}</span>
              </div>
              <div className={styles.finRow}>
                <span className={styles.finLabel}>💸 Выведено всего</span>
                <span className={styles.finValueOut}>{formatRub(stats.financial.total_payouts)}</span>
              </div>
              <div className={`${styles.finRow} ${styles.finRowTotal}`}>
                <span className={styles.finLabel}>📊 Оборот (внесено − выведено)</span>
                <span className={styles.finValueNet}>{formatRub(stats.financial.net_balance)}</span>
              </div>
              <div className={styles.finDivider} />
              <div className={styles.finRow}>
                <span className={styles.finLabel}>🔒 В эскроу сейчас</span>
                <span className={styles.finValueNeutral}>{formatRub(stats.financial.escrow_reserved)}</span>
              </div>
              <div className={styles.finRow}>
                <span className={styles.finLabel}>⏳ Ожидают вывода</span>
                <span className={styles.finValueNeutral}>{formatRub(stats.financial.payout_reserved)}</span>
              </div>
              <div className={styles.finDivider} />
              <div className={styles.finRow}>
                <span className={styles.finLabel}>⭐ Комиссия платформы</span>
                <span className={styles.finValueIn}>{formatRub(stats.financial.profit_accumulated)}</span>
              </div>
            </div>
          </Card>
        </div>

        {/* Back to Main Menu Button */}
        <div className={styles.backButtonWrap}>
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
