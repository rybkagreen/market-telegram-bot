import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Notification, Skeleton, Button } from '@shared/ui'
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
    <div className="space-y-6 pb-24">
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
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {channels?.map((channel) => (
            <Card key={channel.id} className="p-5">
              <div className="flex items-start gap-4">
                {/* Avatar */}
                <div className="w-12 h-12 rounded-full bg-accent-muted flex items-center justify-center text-xl shrink-0">
                  {channel.title[0]?.toUpperCase() ?? '📺'}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <h3 className="font-semibold text-text-primary truncate">{channel.title}</h3>
                      <p className="text-sm text-text-tertiary">@{channel.username}</p>
                    </div>

                    {/* Icon action buttons */}
                    <div className="flex items-center gap-1 shrink-0">
                      {/* Compare toggle */}
                      <button
                        className={`w-9 h-9 rounded-md flex items-center justify-center text-sm font-medium transition-colors ${
                          compareIds.has(channel.id)
                            ? 'bg-accent text-accent-text'
                            : compareIds.size >= MAX_COMPARE
                            ? 'text-text-tertiary cursor-not-allowed'
                            : 'text-text-secondary hover:bg-harbor-elevated hover:text-text-primary'
                        }`}
                        title={compareIds.has(channel.id) ? 'Убрать из сравнения' : 'Добавить к сравнению'}
                        disabled={!compareIds.has(channel.id) && compareIds.size >= MAX_COMPARE}
                        onClick={() => toggleCompare(channel.id)}
                      >
                        ⚖️
                      </button>

                      <button
                        className="w-9 h-9 rounded-md flex items-center justify-center text-text-secondary hover:bg-harbor-elevated hover:text-text-primary transition-colors"
                        title="Настройки"
                        onClick={() => navigate(`/own/channels/${channel.id}/settings`)}
                      >
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.24-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.507 6.507 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.753-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z" />
                          <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
                        </svg>
                      </button>
                      <button
                        className={`w-9 h-9 rounded-md flex items-center justify-center transition-colors ${
                          deletingChannelId === channel.id
                            ? 'text-text-tertiary cursor-wait'
                            : 'text-text-secondary hover:bg-danger-muted hover:text-danger'
                        }`}
                        title="Удалить"
                        disabled={deletingChannelId !== null}
                        onClick={() => handleDeleteChannel(channel.id, channel.title)}
                      >
                        {deletingChannelId === channel.id ? (
                          <span className="w-4 h-4 border-2 border-text-tertiary border-t-transparent rounded-full animate-spin" />
                        ) : (
                          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
                          </svg>
                        )}
                      </button>
                    </div>
                  </div>

                  {/* Stats row */}
                  <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-sm">
                    <span className="text-text-secondary">👥 {channel.member_count.toLocaleString('ru-RU')}</span>
                    <span className="text-text-secondary">⭐ {channel.rating.toFixed(1)}</span>
                    <span className={channel.is_active ? 'text-success' : 'text-text-tertiary'}>
                      {channel.is_active ? 'Активен' : 'Неактивен'}
                    </span>
                  </div>

                  {/* Category */}
                  <div className="mt-3">
                    {!channel.category ? (
                      <div className="bg-warning-muted rounded-md p-3">
                        <p className="text-sm text-warning mb-2">⚠️ Выберите категорию — канал не виден рекламодателям</p>
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
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-accent-muted text-accent">
                        {CATEGORY_OPTIONS.find((c) => c.key === channel.category)?.emoji}{' '}
                        {CATEGORY_OPTIONS.find((c) => c.key === channel.category)?.label ?? channel.category}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </Card>
          ))}
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
