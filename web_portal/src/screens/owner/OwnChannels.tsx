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
              <Card key={channel.id} className="p-4 hover:shadow-lg transition-shadow">
                {/* Main row: Identity | Metrics | Actions */}
                <div className="flex flex-col sm:grid sm:grid-cols-12 gap-3 sm:items-center">
                  {/* Zone A: Identity (col-span-5) */}
                  <div className="sm:col-span-5 flex items-start gap-2 sm:gap-3 min-w-0">
                    {/* Avatar */}
                    <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-accent-muted flex items-center justify-center text-base sm:text-lg shrink-0">
                      {channel.title[0]?.toUpperCase() ?? '📺'}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="text-sm font-semibold text-text-primary truncate">
                          @{channel.username}
                        </span>
                        <StatusPill status={statusPill.status} size="sm">{statusPill.label}</StatusPill>
                      </div>
                      <p className="text-sm text-text-secondary truncate">{channel.title}</p>
                      {categoryLabel ? (
                        <span className="inline-flex items-center gap-1 mt-1 px-2 py-0.5 rounded-full text-xs font-medium bg-accent-muted text-accent">
                          {categoryLabel.emoji} {categoryLabel.label}
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 mt-1 px-2 py-0.5 rounded-full text-xs font-medium bg-warning-muted text-warning">
                          ⚠️ Без категории
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Zone B: Metrics (col-span-3) */}
                  <div className="sm:col-span-3 sm:border-l sm:border-border sm:pl-4 flex items-center justify-center bg-harbor-elevated/30 sm:bg-transparent rounded-md sm:rounded-none px-3 py-2 sm:py-0">
                    <div className="text-center">
                      <p className="text-base font-semibold text-text-primary">{channel.member_count.toLocaleString('ru-RU')}</p>
                      <p className="text-[10px] text-text-tertiary">подписчики</p>
                    </div>
                    <div className="w-px h-8 bg-border mx-3" />
                    <div className="text-center">
                      <p className="text-base font-semibold text-text-primary">{channel.rating.toFixed(1)}</p>
                      <p className="text-[10px] text-text-tertiary">рейтинг</p>
                    </div>
                  </div>

                  {/* Zone C: Actions (col-span-4) */}
                  <div className="sm:col-span-4 sm:border-l sm:border-border sm:pl-4 flex items-center justify-end gap-1 sm:gap-2 flex-wrap">
                    {/* Compare — text on desktop, icon only on mobile */}
                    <button
                      className={`px-2 py-1.5 sm:px-3 sm:py-1.5 rounded-md text-xs font-medium transition-colors flex items-center gap-1 ${
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
                      <span>⚖️</span>
                      <span className="hidden sm:inline">Сравнить</span>
                    </button>
                    {/* Settings — icon only on mobile, icon+text on desktop */}
                    <Button
                      variant="secondary"
                      size="sm"
                      className="px-2 sm:px-3"
                      onClick={() => navigate(`/own/channels/${channel.id}/settings`)}
                    >
                      <span>⚙️</span>
                      <span className="hidden sm:inline ml-1">Настр.</span>
                    </Button>
                    {/* Delete — icon only on mobile, icon+text on desktop */}
                    <Button
                      variant="danger"
                      size="sm"
                      className="px-2 sm:px-3"
                      disabled={deletingChannelId !== null}
                      onClick={() => handleDeleteChannel(channel.id, channel.title)}
                    >
                      {deletingChannelId === channel.id ? (
                        <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                      ) : (
                        <>
                          <span>🗑️</span>
                          <span className="hidden sm:inline ml-1">Удалить</span>
                        </>
                      )}
                    </Button>
                  </div>
                </div>

                {/* Category inline picker (only when missing) */}
                {!channel.category && (
                  <div className="mt-2">
                    <p className="text-xs text-warning mb-1.5">⚠️ Добавьте категорию — без неё канал не виден рекламодателям</p>
                    {editingCategoryFor === channel.id ? (
                      <div className="flex flex-wrap gap-1.5">
                        {CATEGORY_OPTIONS.map((cat) => (
                          <button
                            key={cat.key}
                            className="px-2 py-1 rounded-md text-xs bg-harbor-elevated text-text-secondary hover:bg-accent-muted hover:text-accent transition-colors"
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
