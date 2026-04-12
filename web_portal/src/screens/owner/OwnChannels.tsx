import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button, StatusPill, Skeleton, EmptyState, Card } from '@shared/ui'
import { useMyChannels, useUpdateChannelCategory } from '@/hooks/useChannelQueries'
import { useDeleteChannel } from '@/hooks/useChannelSettings'
import { CATEGORIES } from '@/lib/constants'

const CATEGORY_OPTIONS = CATEGORIES.map((c) => ({ key: c.key, label: c.name, emoji: c.emoji }))
const MAX_COMPARE = 3

type SortKey = 'members' | 'rating' | 'name'
type SortDir = 'asc' | 'desc'
type Filter = 'active' | 'inactive' | 'all'
const PAGE_SIZE = 10

const EMPTY_SUBTITLE: Record<Filter, string> = {
  active: 'Нет активных каналов',
  inactive: 'Нет неактивных каналов',
  all: 'У вас пока нет каналов — добавьте первый!',
}

interface ChannelData {
  id: number
  title: string
  username: string
  member_count: number
  rating: number
  is_active: boolean
  category?: string | null
  avg_views?: number | null
  last_er?: number | null
}

function CompareModal({ channels, onClose }: { channels: ChannelData[]; onClose: () => void }) {
  const dialogRef = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const dialog = dialogRef.current
    dialog?.showModal()
    return () => dialog?.close()
  }, [])

  const metrics: { key: keyof ChannelData; label: string; format: (v: unknown) => string }[] = [
    { key: 'member_count', label: 'Подписчики', format: (v) => Number(v).toLocaleString('ru-RU') },
    { key: 'avg_views', label: 'Avg views', format: (v) => v != null ? Number(v).toLocaleString('ru-RU') : '—' },
    { key: 'last_er', label: 'ER%', format: (v) => v != null ? `${(Number(v) * 100).toFixed(1)}%` : '—' },
    { key: 'rating', label: 'Рейтинг', format: (v) => `${Number(v).toFixed(1)} ⭐` },
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

function SortIcon({ active, dir }: { active: boolean; dir: SortDir }) {
  if (!active) return <span className="text-text-tertiary ml-1">↕</span>
  return <span className="text-accent ml-1">{dir === 'asc' ? '↑' : '↓'}</span>
}

export default function OwnChannels() {
  const navigate = useNavigate()
  const { data: channels, isLoading, isError, refetch } = useMyChannels()
  const updateCategory = useUpdateChannelCategory()
  const deleteChannel = useDeleteChannel()
  const [filter, setFilter] = useState<Filter>('all')
  const [sortKey, setSortKey] = useState<SortKey>('name')
  const [sortDir, setSortDir] = useState<SortDir>('asc')
  const [page, setPage] = useState(0)
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

  const activeCnt = (channels ?? []).filter((c) => c.is_active).length
  const inactiveCnt = (channels ?? []).filter((c) => !c.is_active).length
  const allCnt = channels?.length ?? 0

  const filtered = (channels ?? []).filter((c) => {
    if (filter === 'active') return c.is_active
    if (filter === 'inactive') return !c.is_active
    return true
  })

  const sorted = [...filtered].sort((a, b) => {
    if (sortKey === 'members') {
      return sortDir === 'asc' ? a.member_count - b.member_count : b.member_count - a.member_count
    }
    if (sortKey === 'rating') {
      return sortDir === 'asc' ? a.rating - b.rating : b.rating - a.rating
    }
    // name
    return sortDir === 'asc'
      ? (a.username || '').localeCompare(b.username || '')
      : (b.username || '').localeCompare(a.username || '')
  })

  const totalPages = Math.ceil(sorted.length / PAGE_SIZE)
  const paged = sorted.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
    setPage(0)
  }

  const handleFilterChange = (f: Filter) => {
    setFilter(f)
    setPage(0)
  }

  const compareChannels = (channels ?? []).filter((ch) => compareIds.has(ch.id))

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-12" />
        <Skeleton className="h-12" />
        <Skeleton className="h-12" />
      </div>
    )
  }

  if (isError) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-display font-bold text-text-primary">Мои каналы</h1>
        </div>
        <EmptyState icon="❌" title="Не удалось загрузить каналы" description="Попробуйте обновить страницу" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-display font-bold text-text-primary">Мои каналы</h1>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" onClick={() => void refetch()}>
            🔄
          </Button>
          <Button variant="primary" size="sm" onClick={() => navigate('/own/channels/add')}>
            ➕ Добавить
          </Button>
        </div>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2 flex-wrap">
        <button
          className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
            filter === 'all'
              ? 'bg-accent-muted text-accent border border-accent/30'
              : 'bg-harbor-card text-text-secondary border border-border hover:border-accent/30'
          }`}
          onClick={() => handleFilterChange('all')}
        >
          📺 Все ({allCnt})
        </button>
        <button
          className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
            filter === 'active'
              ? 'bg-success-muted text-success border border-success/30'
              : 'bg-harbor-card text-text-secondary border border-border hover:border-success/30'
          }`}
          onClick={() => handleFilterChange('active')}
        >
          ✅ Активные ({activeCnt})
        </button>
        <button
          className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
            filter === 'inactive'
              ? 'bg-danger-muted text-danger border border-danger/30'
              : 'bg-harbor-card text-text-secondary border border-border hover:border-danger/30'
          }`}
          onClick={() => handleFilterChange('inactive')}
        >
          ⛔ Неактивные ({inactiveCnt})
        </button>
      </div>

      {/* List */}
      {sorted.length === 0 ? (
        <EmptyState
          icon="📺"
          title="Нет каналов"
          description={EMPTY_SUBTITLE[filter]}
          action={
            filter === 'all' || filter === 'active'
              ? { label: '➕ Добавить канал', onClick: () => navigate('/own/channels/add') }
              : undefined
          }
        />
      ) : (
        <>
          {/* Desktop table */}
          <div className="hidden md:block">
            <Card className="p-0 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-harbor-elevated">
                    <tr>
                      <th
                        className="text-left px-4 py-3 text-text-secondary font-medium cursor-pointer select-none hover:text-text-primary"
                        onClick={() => toggleSort('name')}
                      >
                        Канал <SortIcon active={sortKey === 'name'} dir={sortDir} />
                      </th>
                      <th
                        className="text-right px-4 py-3 text-text-secondary font-medium cursor-pointer select-none hover:text-text-primary"
                        onClick={() => toggleSort('members')}
                      >
                        Подписчики <SortIcon active={sortKey === 'members'} dir={sortDir} />
                      </th>
                      <th
                        className="text-right px-4 py-3 text-text-secondary font-medium cursor-pointer select-none hover:text-text-primary"
                        onClick={() => toggleSort('rating')}
                      >
                        Рейтинг <SortIcon active={sortKey === 'rating'} dir={sortDir} />
                      </th>
                      <th className="text-left px-4 py-3 text-text-secondary font-medium hidden lg:table-cell">Категория</th>
                      <th className="text-left px-4 py-3 text-text-secondary font-medium">Статус</th>
                      <th className="text-right px-4 py-3 text-text-secondary font-medium">Действия</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {paged.map((channel) => {
                      const statusPill = channel.is_active
                        ? { status: 'success' as const, label: '✅ Активен' }
                        : { status: 'danger' as const, label: '⛔ Неактивен' }
                      const categoryLabel = channel.category
                        ? CATEGORY_OPTIONS.find((c) => c.key === channel.category)
                        : null
                      const isDeletingThis = deletingChannelId === channel.id

                      return (
                        <tr key={channel.id} className="hover:bg-harbor-elevated/50 transition-colors">
                          <td className="px-4 py-3">
                            <p className="font-medium text-text-primary">
                              @{channel.username}
                            </p>
                            <p className="text-xs text-text-tertiary truncate">{channel.title}</p>
                          </td>
                          <td className="px-4 py-3 text-right font-mono text-text-primary">
                            {channel.member_count.toLocaleString('ru-RU')}
                          </td>
                          <td className="px-4 py-3 text-right font-mono text-text-primary">
                            {channel.rating.toFixed(1)}
                          </td>
                          <td className="px-4 py-3 hidden lg:table-cell">
                            {categoryLabel ? (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-accent-muted text-accent">
                                {categoryLabel.emoji} {categoryLabel.label}
                              </span>
                            ) : (
                              <span className="text-xs text-warning">⚠️ Нет категории</span>
                            )}
                          </td>
                          <td className="px-4 py-3">
                            <StatusPill status={statusPill.status}>{statusPill.label}</StatusPill>
                          </td>
                          <td className="px-4 py-3 text-right">
                            <div className="flex gap-1.5 justify-end">
                              <button
                                className={`px-2 py-1.5 rounded-md text-xs font-medium transition-colors ${
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
                                ⚖️
                              </button>
                              <Button variant="secondary" size="sm" onClick={() => navigate(`/own/channels/${channel.id}/settings`)}>
                                ⚙️
                              </Button>
                              <Button
                                variant="danger"
                                size="sm"
                                disabled={deletingChannelId !== null}
                                onClick={() => handleDeleteChannel(channel.id, channel.title)}
                              >
                                {isDeletingThis ? '⏳' : '🗑️'}
                              </Button>
                            </div>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>

          {/* Mobile cards */}
          <div className="md:hidden space-y-4">
            {paged.map((channel) => {
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

                  <div className="flex gap-2">
                    <button
                      className={`flex items-center justify-center rounded-md border transition-colors min-h-[44px] min-w-[44px] ${
                        compareIds.has(channel.id)
                          ? 'bg-accent text-accent-text border-accent'
                          : compareIds.size >= MAX_COMPARE
                          ? 'text-text-tertiary cursor-not-allowed border-border'
                          : 'bg-harbor-elevated text-text-secondary border-border hover:bg-accent-muted hover:text-accent'
                      }`}
                      title={compareIds.has(channel.id) ? 'Убрать из сравнения' : 'Добавить к сравнению'}
                      disabled={!compareIds.has(channel.id) && compareIds.size >= MAX_COMPARE}
                      onClick={() => toggleCompare(channel.id)}
                    >
                      ⚖️
                    </button>
                    <Button
                      variant="secondary"
                      size="sm"
                      icon
                      onClick={() => navigate(`/own/channels/${channel.id}/settings`)}
                      title="Настройки"
                    >
                      ⚙️
                    </Button>
                    <Button
                      variant="danger"
                      size="sm"
                      icon
                      disabled={deletingChannelId === channel.id}
                      onClick={() => handleDeleteChannel(channel.id, channel.title)}
                      title="Удалить"
                    >
                      {deletingChannelId === channel.id ? '⏳' : '🗑️'}
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

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between">
              <Button size="sm" variant="secondary" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
                ← Назад
              </Button>
              <span className="text-sm text-text-secondary">
                Страница {page + 1} из {totalPages} ({sorted.length} всего)
              </span>
              <Button size="sm" variant="secondary" disabled={page + 1 >= totalPages} onClick={() => setPage((p) => p + 1)}>
                Далее →
              </Button>
            </div>
          )}
        </>
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
