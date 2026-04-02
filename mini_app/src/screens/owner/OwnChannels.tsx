import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Button, CategoryGrid, ChannelCard, Notification, Skeleton } from '@/components/ui'
import { formatCompact } from '@/lib/formatters'
import { useMyChannels, useUpdateChannelCategory } from '@/hooks/queries/useChannelQueries'
import { useCategories } from '@/hooks/queries/useCategoryQueries'
import styles from './OwnChannels.module.css'

export default function OwnChannels() {
  const navigate = useNavigate()
  const { data: channels, isLoading, isError, refetch } = useMyChannels()
  const { data: categories = [] } = useCategories()
  const updateCategory = useUpdateChannelCategory()
  const [editingCategoryFor, setEditingCategoryFor] = useState<number | null>(null)

  const handleCategorySelect = (channelId: number, categoryKey: string) => {
    updateCategory.mutate(
      { id: channelId, category: categoryKey },
      { onSuccess: () => setEditingCategoryFor(null) },
    )
  }

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

                {!channel.category && (
                  <div className={styles.categoryWarning}>
                    <Notification type="warning">
                      <span style={{ fontSize: 'var(--rh-text-sm)' }}>
                        ⚠️ Канал не виден рекламодателям — выберите категорию
                      </span>
                      <div className={styles.categoryActions}>
                        {editingCategoryFor === channel.id ? (
                          <CategoryGrid
                            categories={categories.map((c) => ({
                              id: c.key,
                              label: c.name,
                              icon: c.emoji,
                            }))}
                            selected={[]}
                            onToggle={(key) => handleCategorySelect(channel.id, key)}
                          />
                        ) : (
                          <Button
                            size="sm"
                            onClick={() => setEditingCategoryFor(channel.id)}
                          >
                            📂 Выбрать категорию
                          </Button>
                        )}
                      </div>
                    </Notification>
                  </div>
                )}
              </div>
            ))}
          </div>
        </>
      )}
    </ScreenShell>
  )
}
