import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Notification, Skeleton, Button, StatusPill } from '@shared/ui'
import { useMyChannels, useUpdateChannelCategory } from '@/hooks/useChannelQueries'
import { useDeleteChannel } from '@/hooks/useChannelSettings'
import { CATEGORIES } from '@/lib/constants'

const CATEGORY_OPTIONS = CATEGORIES.map((c) => ({ key: c.key, label: c.name, emoji: c.emoji }))
const MAX_COMPARE = 3

interface ChannelData {
  id: number
  title: string
  username: string
  member_count: number
  rating: number
  is_active: boolean
  category?: string | null
  avg_post_views?: number | null
  last_er?: number | null
  price_per_post?: number | null
}

function CompareModal({ channels, onClose }: { channels: ChannelData[]; onClose: () => void }) {
  const dialogRef = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    dialogRef.current?.showModal()
    return () => dialogRef.current?.close()
  }, [])

  const metrics: { key: keyof ChannelData; label: string; format: (v: unknown) => string }[] = [
    { key: 'member_count', label: 'Подписчики', format: (v) => Number(v).toLocaleString('ru-RU') },
    { key: 'avg_post_views', label: 'Avg views', format: (v) => v != null ? Number(v).toLocaleString('ru-RU') : '—' },
    { key: 'last_er', label: 'ER%', format: (v) => v != null ? `${(Number(v) * 100).toFixed(1)}%` : '—' },
    { key: 'rating', label: 'Рейтинг', format: (v) => `${Number(v).toFixed(1)} ⭐` },
    { key: 'price_per_post', label: 'Цена за пост', format: (v) => v != null ? `${Number(v).toLocaleString('ru-RU')} ₽` : '—' },
    { key: 'category', label: 'Категория', format: (v) => {
      if (!v) return '—'
      const cat = CATEGORY_OPTIONS.find((c) => c.key === String(v))
      return cat ? `${cat.emoji} ${cat.label}` : String(v)
    }},
    { key: 'is_active', label: 'Статус', format: (v) => v ? '✅ Активен' : '⛔ Неактивен' },
  ]

  return (
    <dialog
      ref={dialogRef}
      className="w-full max-w-3xl rounded-xl bg-harbor-card border border-border shadow-2xl p-0 backdrop:bg-black/60"
      onClick={(e) => { if (e.target === dialogRef.current) onClose() }}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { if (e.target === dialogRef.current) onClose() } }}
      role="button"
      tabIndex={0}
    >
      <div className="flex items-center justify-between px-6 py-4 border-b border-border">
        <h2 className="text-lg font-display font-bold text-text-primary">Сравнение каналов</h2>
        <button
          className="w-8 h-8 flex items-center justify-center rounded-md text-text-secondary hover:text-text-primary hover:bg-harbor-elevated transition-colors"
          onClick={onClose}
        >
          ✕
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-harbor-elevated">
            <tr>
              <th className="text-left px-4 py-3 text-text-secondary font-medium w-32">Метрика</th>
              {channels.map((ch) => (
                <th key={ch.id} className="text-center px-4 py-3 text-text-primary font-semibold">
                  <p>{ch.title}</p>
                  <p className="text-xs text-text-tertiary font-normal">@{ch.username}</p>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {metrics.map(({ key, label, format }) => (
              <tr key={key} className="hover:bg-harbor-elevated/30 transition-colors">
                <td className="px-4 py-3 text-text-secondary">{label}</td>
                {channels.map((ch) => (
                  <td key={ch.id} className="px-4 py-3 text-center text-text-primary font-mono">
                    {format(ch[key])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="px-6 py-4 border-t border-border flex justify-end">
        <Button variant="secondary" onClick={onClose}>Закрыть</Button>
      </div>
    </dialog>
  )
}

export default function OwnChannels() {
  const navigate = useNavigate()
  const { data: channels, isLoading, isError, refetch } = useMyChannels()
  const updateCategory = useUpdateChannelCategory()
  const deleteChannel = useDeleteChannel()
  const [editingCategoryFor, setEditingCategoryFor] = useState<number | null>(null)
  const [deletingChannelId, setDeletingChannelId] = useState<number | null>(null)
  const [compareIds, setCompareIds] = useState<Set<number>>(new Set())
  const [showCompare, setShowCompare] = useState(false)

  const handleDeleteChannel = (channelId: number, channelTitle: string) => {
    if (confirm(`Удалить канал "${channelTitle}"? Это действие нельзя отменить.`)) {
      setDeletingChannelId(channelId)
      deleteChannel.mutate(channelId, {
        onSuccess: () => setDeletingChannelId(null),
        onError: () => {
          setDeletingChannelId(null)
          alert('Не удалось удалить канал. Попробуйте позже.')
        },
      })
    }
  }

  const toggleCompare = (id: number) => {
    setCompareIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else if (next.size < MAX_COMPARE) {
        next.add(id)
      }
      return next
    })
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-12" />
        {[1, 2, 3].map((i) => <Skeleton key={i} className="h-28" />)}
      </div>
    )
  }

  if (isError) {
    return <Notification type="danger">❌ Не удалось загрузить каналы</Notification>
  }

  const compareChannels = (channels ?? []).filter((ch) => compareIds.has(ch.id))

  return (
    <div className="space-y-6 pb-24 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-display font-bold text-text-primary">Мои каналы</h1>
          <p className="text-text-secondary mt-1">{channels?.length ?? 0} каналов</p>
        </div>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={() => refetch()}>🔄</Button>
          <Button size="sm" onClick={() => navigate('/own/channels/add')}>➕ Добавить</Button>
        </div>
      </div>

      {/* Channel list */}
      {channels && channels.length === 0 ? (
        <Card className="p-8 text-center">
          <p className="text-text-secondary mb-4">У вас пока нет каналов</p>
          <Button onClick={() => navigate('/own/channels/add')}>➕ Добавить первый канал</Button>
        </Card>
      ) : (
        <div className="space-y-4">
          {channels?.map((channel) => {
            const statusPill = channel.is_active
              ? { status: 'success' as const, label: '✅ Активен' }
              : { status: 'danger' as const, label: '⛔ Неактивен' }

            const categoryLabel = channel.category
              ? CATEGORY_OPTIONS.find((c) => c.key === channel.category)
              : null

            return (
              <Card key={channel.id} className="p-4">
                <div className="flex items-start justify-between gap-4 mb-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-semibold text-text-primary">
                        #{channel.id} · @{channel.username}
                      </span>
                      <StatusPill status={statusPill.status}>{statusPill.label}</StatusPill>
                    </div>
                    <p className="text-sm text-text-secondary truncate">{channel.title}</p>
                    <div className="flex gap-4 mt-2 text-xs text-text-tertiary">
                      <span>👥 {channel.member_count.toLocaleString('ru-RU')}</span>
                      <span>⭐ {channel.rating.toFixed(1)}</span>
                      {categoryLabel && (
                        <span>{categoryLabel.emoji} {categoryLabel.label}</span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex gap-2 flex-wrap">
                  <button
                    className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                      compareIds.has(channel.id)
                        ? 'bg-accent text-accent-text'
                        : compareIds.size >= MAX_COMPARE
                        ? 'text-text-tertiary cursor-not-allowed'
                        : 'bg-harbor-elevated text-text-secondary hover:bg-accent-muted hover:text-accent'
                    }`}
                    title={compareIds.has(channel.id) ? 'Убрать из сравнения' : 'Добавить к сравнению'}
                    disabled={!compareIds.has(channel.id) && compareIds.size >= MAX_COMPARE}
                    onClick={() => toggleCompare(channel.id)}
                  >
                    ⚖️ Сравнить
                  </button>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => navigate(`/own/channels/${channel.id}/settings`)}
                  >
                    ⚙️ Настройки
                  </Button>
                  <Button
                    variant="danger"
                    size="sm"
                    disabled={deletingChannelId !== null}
                    onClick={() => handleDeleteChannel(channel.id, channel.title)}
                  >
                    {deletingChannelId === channel.id ? '⏳...' : '🗑️ Удалить'}
                  </Button>
                </div>

                {/* Category inline picker (only when missing) */}
                {!channel.category && (
                  <div className="mt-3 pt-3 border-t border-border">
                    <p className="text-sm text-warning mb-2">⚠️ Канал без категории — не виден рекламодателям. Добавьте категорию через кнопку ниже.</p>
                    {editingCategoryFor === channel.id ? (
                      <div className="flex flex-wrap gap-1.5">
                        {CATEGORY_OPTIONS.map((cat) => (
                          <button
                            key={cat.key}
                            className="px-2.5 py-1 rounded-md text-xs bg-harbor-elevated text-text-secondary hover:bg-accent-muted hover:text-accent transition-colors"
                            onClick={() => {
                              updateCategory.mutate({ id: channel.id, category: cat.key })
                              setEditingCategoryFor(null)
                            }}
                          >
                            {cat.emoji} {cat.label}
                          </button>
                        ))}
                      </div>
                    ) : (
                      <Button size="sm" variant="secondary" onClick={() => setEditingCategoryFor(channel.id)}>
                        📂 Выбрать категорию
                      </Button>
                    )}
                  </div>
                )}
              </Card>
            )
          })}
        </div>
      )}

      {/* Compare sticky bar */}
      {compareIds.size >= 2 && (
        <div className="fixed bottom-0 left-0 right-0 z-40 bg-harbor-card border-t border-border shadow-2xl px-4 py-3">
          <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
            <span className="text-sm text-text-secondary">
              ⚖️ Сравниваете <strong className="text-text-primary">{compareIds.size}</strong> канала
            </span>
            <div className="flex gap-2">
              <Button variant="ghost" size="sm" onClick={() => setCompareIds(new Set())}>
                Сбросить
              </Button>
              <Button variant="primary" size="sm" onClick={() => setShowCompare(true)}>
                Сравнить →
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Compare modal */}
      {showCompare && compareChannels.length >= 2 && (
        <CompareModal
          channels={compareChannels as ChannelData[]}
          onClose={() => setShowCompare(false)}
        />
      )}
    </div>
  )
}
