import { useLocation, useParams } from 'react-router-dom'

import { ScreenShell } from '@/components/layout/ScreenShell'
import { Card, EmptyState, Skeleton, Text } from '@/components/ui'
import { useChannelMediakit } from '@/hooks/queries'

interface NavState {
  channelTitle?: string
  channelUsername?: string
}

export default function ChannelMediakitView() {
  const { channelId } = useParams<{ channelId: string }>()
  const location = useLocation()
  const navState = (location.state ?? {}) as NavState
  const numericId = channelId ? Number(channelId) : null
  const query = useChannelMediakit(Number.isFinite(numericId) ? numericId : null)

  if (query.isLoading) {
    return (
      <ScreenShell>
        <Text variant="lg" weight="semibold" as="h1">Медиакит</Text>
        <div style={{ marginTop: 'var(--rh-space-4)', display: 'flex', flexDirection: 'column', gap: 'var(--rh-space-3)' }}>
          <Skeleton height={80} radius="md" />
          <Skeleton height={120} radius="md" />
          <Skeleton height={120} radius="md" />
        </div>
      </ScreenShell>
    )
  }

  if (query.isError || !query.data) {
    return (
      <ScreenShell>
        <Text variant="lg" weight="semibold" as="h1">Медиакит</Text>
        <div style={{ marginTop: 'var(--rh-space-6)' }}>
          <EmptyState
            icon="📭"
            title="Медиакит недоступен"
            description="Владелец канала ещё не опубликовал медиакит."
          />
        </div>
      </ScreenShell>
    )
  }

  const mediakit = query.data
  const channelLabel = navState.channelTitle
    ? `${navState.channelTitle}${navState.channelUsername ? ` · @${navState.channelUsername}` : ''}`
    : null
  const updatedDate = new Date(mediakit.updated_at).toLocaleDateString('ru-RU')

  return (
    <ScreenShell>
      <Text variant="lg" weight="semibold" as="h1">Медиакит</Text>
      {channelLabel && (
        <div style={{ marginTop: 'var(--rh-space-1)' }}>
          <Text variant="sm" color="muted">{channelLabel}</Text>
        </div>
      )}

      <div style={{ marginTop: 'var(--rh-space-4)', display: 'flex', flexDirection: 'column', gap: 'var(--rh-space-3)' }}>
        <Card title="Средний охват поста">
          <Text variant="xl" weight="bold">
            {mediakit.avg_post_reach.toLocaleString('ru-RU')}
          </Text>
        </Card>

        {mediakit.description && (
          <Card title="Описание канала">
            <Text variant="md">{mediakit.description}</Text>
          </Card>
        )}

        {mediakit.audience_description && (
          <Card title="Аудитория">
            <Text variant="md">{mediakit.audience_description}</Text>
          </Card>
        )}

        {/* Logo display deferred — no Telegram file_id → image resolver exists (BACKLOG). */}

        <div style={{ marginTop: 'var(--rh-space-2)', textAlign: 'right' }}>
          <Text variant="sm" color="muted">Обновлено {updatedDate}</Text>
        </div>
      </div>
    </ScreenShell>
  )
}
