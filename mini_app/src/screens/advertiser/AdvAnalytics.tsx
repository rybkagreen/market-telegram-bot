import { ScreenShell } from '@/components/layout/ScreenShell'
import { StatGrid, Card, Notification, Skeleton, Button } from '@/components/ui'
import { formatCurrency, formatCompact, formatPercent } from '@/lib/formatters'
import { useAdvertiserAnalytics } from '@/hooks/queries'
import styles from './AdvAnalytics.module.css'

export default function AdvAnalytics() {
  const { data: analytics, isLoading, isError, refetch } = useAdvertiserAnalytics()
  const topChannel = analytics?.top_channels[0]

  return (
    <ScreenShell>
      {isLoading ? (
        <>
          <Skeleton height={80} />
          <Skeleton height={200} />
        </>
      ) : isError ? (
        <Notification type="danger">
          <span>Не удалось загрузить аналитику.</span>{' '}
          <Button variant="secondary" size="sm" onClick={() => refetch()}>
            Повторить
          </Button>
        </Notification>
      ) : analytics ? (
        <>
          <StatGrid
            items={[
              { value: String(analytics.total_campaigns), label: 'Кампаний', color: 'blue' },
              { value: formatCompact(analytics.total_reach), label: 'Охват', color: 'green' },
              { value: formatPercent(analytics.avg_ctr), label: 'CTR', color: 'yellow' },
              { value: formatCurrency(analytics.total_spent), label: 'Потрачено', color: 'purple' },
            ]}
          />

          <p className={styles.sectionTitle}>Топ каналов по охвату</p>

          <Card>
            {analytics.top_channels.map((ch) => (
              <div key={ch.channel.username} className={styles.channelRow}>
                <span className={styles.channelName}>@{ch.channel.username}</span>
                <span className={styles.channelReach}>
                  {formatCompact(ch.reach)} 👁
                </span>
              </div>
            ))}
          </Card>

          {topChannel && (
            <Notification type="success">
              <span style={{ fontSize: 'var(--rh-text-sm)' }}>
                ✨ AI-рекомендация: Увеличьте бюджет на IT-каналы (высокий CTR {topChannel.ctr}%)
              </span>
            </Notification>
          )}
        </>
      ) : null}
    </ScreenShell>
  )
}
