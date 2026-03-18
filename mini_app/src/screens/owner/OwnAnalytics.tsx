import { ScreenShell } from '@/components/layout/ScreenShell'
import { StatGrid, Card, Skeleton, Notification } from '@/components/ui'
import { formatCurrency } from '@/lib/formatters'
import { useOwnerAnalytics } from '@/hooks/queries/useAnalyticsQueries'
import styles from './OwnAnalytics.module.css'

export default function OwnAnalytics() {
  const { data: analytics, isLoading, isError } = useOwnerAnalytics()

  if (isLoading) {
    return (
      <ScreenShell>
        <Skeleton height={80} radius="lg" />
        <Skeleton height={200} radius="lg" />
        <Skeleton height={150} radius="lg" />
      </ScreenShell>
    )
  }

  // ИЗМЕНЕНО (UX-P0): Разделена обработка isError и !analytics
  if (isError) {
    console.error('[OwnAnalytics] Analytics error:', isError) // ДОБАВЛЕНО (UX-P0)
    return (
      <ScreenShell>
        <Notification type="danger">
          <span style={{ fontSize: 'var(--rh-text-sm)' }}>❌ Не удалось загрузить аналитику</span>
        </Notification>
      </ScreenShell>
    )
  }

  if (!analytics) {
    console.warn('[OwnAnalytics] No analytics data') // ДОБАВЛЕНО (UX-P0)
    return null // ИЗМЕНЕНО (UX-P0): было Notification
  }

  return (
    <ScreenShell>
      <StatGrid
        items={[
          { value: formatCurrency(analytics.total_earned), label: 'Заработано', color: 'green' },
          { value: String(analytics.total_publications), label: 'Публикаций', color: 'blue' },
          { value: String(analytics.avg_rating) + '⭐', label: 'Рейтинг', color: 'yellow' },
          { value: String(analytics.channel_count), label: 'Каналов', color: 'purple' },
        ]}
      />

      <p className={styles.sectionTitle}>По каналам</p>

      <Card>
        {analytics.by_channel.map((ch) => (
          <div key={ch.channel.id} className={styles.row}>
            <span className={styles.channelName}>@{ch.channel.username}</span>
            <span className={styles.earned}>{formatCurrency(ch.earned)}</span>
          </div>
        ))}
      </Card>

      <p className={styles.sectionTitle}>Заработок за период</p>

      <Card>
        <div className={styles.row}>
          <span className={styles.periodLabel}>Сегодня</span>
          <span className={styles.periodValue}>{formatCurrency(analytics.earnings_period.today)}</span>
        </div>
        <div className={styles.row}>
          <span className={styles.periodLabel}>Эта неделя</span>
          <span className={styles.periodValue}>{formatCurrency(analytics.earnings_period.week)}</span>
        </div>
        <div className={styles.row}>
          <span className={styles.periodLabel}>Этот месяц</span>
          <span className={styles.periodValue}>{formatCurrency(analytics.earnings_period.month)}</span>
        </div>
      </Card>
    </ScreenShell>
  )
}
