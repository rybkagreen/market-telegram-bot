import { useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { ChannelCard, Skeleton, Notification } from '@/components/ui'
import { formatCompact } from '@/lib/formatters'
import { useMyChannels } from '@/hooks/queries/useChannelQueries'
import styles from './OwnChannels.module.css'

export default function OwnChannels() {
  const navigate = useNavigate()
  const { data: channels, isLoading, isError, refetch } = useMyChannels()

  return (
    <ScreenShell>
      <button
        className={styles.addButton}
        onClick={() => navigate('/own/channels/add')}
      >
        ➕ Добавить канал
      </button>

      {isLoading && (
        <div className={styles.list}>
          <Skeleton height={80} radius="lg" />
          <Skeleton height={80} radius="lg" />
          <Skeleton height={80} radius="lg" />
        </div>
      )}

      {isError && (
        <Notification type="danger">
          <span style={{ fontSize: 'var(--rh-text-sm)' }}>❌ Не удалось загрузить каналы</span>
        </Notification>
      )}

      {!isLoading && !isError && channels && (
        <>
          <button className={styles.refreshButton} onClick={() => refetch()}>
            🔄 Обновить
          </button>

          <div className={styles.list}>
            {channels.map((channel) => (
              <div key={channel.id} className={styles.channelItem}>
                <ChannelCard
                  name={channel.title}
                  username={channel.username}
                  subscribers={formatCompact(channel.member_count)}
                  category={channel.category}
                  status={channel.is_active ? 'active' : 'inactive'}
                  onClick={() => navigate(`/own/channels/${channel.id}`)}
                />
              </div>
            ))}
          </div>
        </>
      )}
    </ScreenShell>
  )
}
