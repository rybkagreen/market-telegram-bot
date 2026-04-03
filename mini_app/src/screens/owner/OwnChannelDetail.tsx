import { useParams, useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { StatGrid, MenuButton, StatusPill, PriceRow, Button, Skeleton, Notification, Text } from '@/components/ui'
import { formatCompact, formatPercent } from '@/lib/formatters'
import { useMyChannels, useChannelSettings, useDeleteChannel } from '@/hooks/queries/useChannelQueries'
import { useHaptic } from '@/hooks/useHaptic'
import styles from './OwnChannelDetail.module.css'

export default function OwnChannelDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const haptic = useHaptic()

  const numericId = id ? parseInt(id) : null

  const { data: channels, isLoading: channelsLoading } = useMyChannels()
  const { data: settings, isLoading: settingsLoading } = useChannelSettings(numericId)
  const deleteMutation = useDeleteChannel()

  const channel = channels?.find((c) => c.id === numericId) ?? null

  const isLoading = channelsLoading || settingsLoading

  const handleDelete = () => {
    haptic.warning()
    if (!numericId) return
    deleteMutation.mutate(numericId, {
      onSuccess: () => { navigate('/own/channels') },
    })
  }

  if (isLoading) {
    return (
      <ScreenShell>
        <Skeleton height={60} radius="lg" />
        <Skeleton height={80} radius="lg" />
        <Skeleton height={120} radius="lg" />
      </ScreenShell>
    )
  }

  if (!channel) {
    return (
      <ScreenShell>
        <Notification type="danger">
          <Text variant="sm">❌ Канал не найден</Text>
        </Notification>
      </ScreenShell>
    )
  }

  return (
    <ScreenShell>
      <div className={styles.header}>
        <div className={styles.avatar}>
          {channel.title.charAt(0)}
        </div>
        <div className={styles.headerInfo}>
          <span className={styles.channelTitle}>{channel.title}</span>
          <span className={styles.channelHandle}>@{channel.username}</span>
        </div>
        <StatusPill status="success">Активен</StatusPill>
      </div>

      <StatGrid
        items={[
          { value: formatCompact(channel.member_count), label: 'Подписчиков', color: 'blue' },
          { value: formatPercent(channel.last_er), label: 'ER', color: 'green' },
          { value: formatCompact(channel.avg_views), label: 'Ср. просмотры', color: 'yellow' },
          { value: String(channel.rating) + '⭐', label: 'Рейтинг', color: 'purple' },
        ]}
      />

      <MenuButton
        icon="⚙️"
        title="Настройки канала"
        subtitle="Цены, форматы, расписание"
        onClick={() => navigate(`/own/channels/${channel.id}/settings`)}
      />

      <MenuButton
        icon="📋"
        iconBg="var(--rh-warning-muted)"
        title="Заявки канала"
        subtitle="Ожидают ответа"
        onClick={() => navigate('/own/requests')}
      />

      {settings && (
        <PriceRow
          label="💰 Базовая цена поста"
          value={settings.price_per_post}
        />
      )}

      <Button
        variant="danger"
        fullWidth
        onClick={handleDelete}
        disabled={deleteMutation.isPending}
      >
        {deleteMutation.isPending ? '⏳ Удаление...' : '🗑 Удалить канал'}
      </Button>
    </ScreenShell>
  )
}
