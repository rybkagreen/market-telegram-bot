import { useState, useRef, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Button,
  Skeleton,
  EmptyState,
  Icon,
  ScreenHeader,
  Notification,
} from '@shared/ui'
import type { IconName } from '@shared/ui'
import { useMyChannels, useUpdateChannelCategory } from '@/hooks/useChannelQueries'
import { useDeleteChannel, useActivateChannel } from '@/hooks/useChannelSettings'
import { CATEGORIES } from '@/lib/constants'

const CATEGORY_OPTIONS = CATEGORIES.map((c) => ({ key: c.key, label: c.name, emoji: c.emoji }))
const MAX_COMPARE = 3
const PAGE_SIZE = 10

type SortKey = 'members' | 'rating' | 'name'
type SortDir = 'asc' | 'desc'
type Filter = 'all' | 'active' | 'inactive'

const EMPTY_SUBTITLE: Record<Filter, string> = {
  all: 'У вас пока нет каналов — добавьте первый.',
  active: 'Нет активных каналов',
  inactive: 'Нет неактивных каналов',
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
    { key: 'avg_views', label: 'Средние просмотры', format: (v) => (v != null ? Number(v).toLocaleString('ru-RU') : '—') },
    { key: 'last_er', label: 'ER', format: (v) => (v != null ? `${(Number(v) * 100).toFixed(1)}%` : '—') },
    { key: 'rating', label: 'Рейтинг', format: (v) => Number(v).toFixed(1) },
    {
      key: 'category',
      label: 'Категория',
      format: (v) => {
        if (!v) return '—'
        const cat = CATEGORY_OPTIONS.find((c) => c.key === String(v))
        return cat ? `${cat.emoji} ${cat.label}` : String(v)
      },
    },
    { key: 'is_active', label: 'Статус', format: (v) => (v ? 'Активен' : 'Неактивен') },
  ]

  return (
    <dialog
      ref={dialogRef}
      className="w-full max-w-3xl rounded-xl bg-harbor-card border border-border shadow-2xl p-0 backdrop:bg-black/60"
      onClick={(e) => {
        if (e.target === dialogRef.current) onClose()
      }}
      onKeyDown={(e) => {
        if (e.key === 'Escape') onClose()
      }}
    >
      <div className="flex items-center justify-between px-6 py-4 border-b border-border">
        <h2 className="font-display text-[15px] font-semibold text-text-primary">
          Сравнение каналов
        </h2>
        <button
          className="w-8 h-8 grid place-items-center rounded-md text-text-secondary hover:text-text-primary hover:bg-harbor-elevated transition-colors"
          onClick={onClose}
          aria-label="Закрыть"
        >
          <Icon name="close" size={14} />
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-harbor-secondary">
            <tr>
              <th className="text-left px-4 py-2.5 text-[11px] uppercase tracking-[0.08em] text-text-tertiary font-semibold w-44">
                Метрика
              </th>
              {channels.map((ch) => (
                <th key={ch.id} className="text-center px-4 py-2.5 text-text-primary font-semibold">
                  <p className="text-[13px]">{ch.title}</p>
                  <p className="text-xs text-text-tertiary font-normal">@{ch.username}</p>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {metrics.map(({ key, label, format }) => (
              <tr key={key} className="hover:bg-harbor-elevated/40 transition-colors">
                <td className="px-4 py-3 text-[13px] text-text-secondary">{label}</td>
                {channels.map((ch) => (
                  <td
                    key={ch.id}
                    className="px-4 py-3 text-center text-text-primary font-mono tabular-nums text-[13px]"
                  >
                    {format(ch[key])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="px-6 py-4 border-t border-border flex justify-end">
        <Button variant="secondary" onClick={onClose}>
          Закрыть
        </Button>
      </div>
    </dialog>
  )
}

export default function OwnChannels() {
  const navigate = useNavigate()
  const { data: channels, isLoading, isError, refetch } = useMyChannels()
  const updateCategory = useUpdateChannelCategory()
  const deleteChannel = useDeleteChannel()
  const activateChannel = useActivateChannel()
  const [filter, setFilter] = useState<Filter>('all')
  const [sortKey, setSortKey] = useState<SortKey>('name')
  const [sortDir, setSortDir] = useState<SortDir>('asc')
  const [page, setPage] = useState(0)
  const [editingCategoryFor, setEditingCategoryFor] = useState<number | null>(null)
  const [deletingChannelId, setDeletingChannelId] = useState<number | null>(null)
  const [compareIds, setCompareIds] = useState<Set<number>>(new Set())
  const [showCompare, setShowCompare] = useState(false)

  const handleDeleteChannel = (channelId: number, channelTitle: string) => {
    if (!confirm(`Скрыть канал «${channelTitle}» от рекламодателей?`)) return
    setDeletingChannelId(channelId)
    deleteChannel.mutate(channelId, {
      onSuccess: () => setDeletingChannelId(null),
      onError: () => {
        setDeletingChannelId(null)
        alert('Не удалось скрыть канал. Попробуйте позже.')
      },
    })
  }

  const handleActivateChannel = (channelId: number, channelTitle: string) => {
    if (!confirm(`Восстановить канал «${channelTitle}»? Он снова станет виден рекламодателям.`))
      return
    activateChannel.mutate(channelId, {
      onError: () => alert('Не удалось восстановить канал. Попробуйте позже.'),
    })
  }

  const toggleCompare = (id: number) => {
    setCompareIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else if (next.size < MAX_COMPARE) next.add(id)
      return next
    })
  }

  const counts = useMemo(() => {
    const list = channels ?? []
    return {
      all: list.length,
      active: list.filter((c) => c.is_active).length,
      inactive: list.filter((c) => !c.is_active).length,
      totalMembers: list.reduce((s, c) => s + (c.member_count || 0), 0),
      withoutCategory: list.filter((c) => !c.category).length,
    }
  }, [channels])

  const filtered = (channels ?? []).filter((c) => {
    if (filter === 'active') return c.is_active
    if (filter === 'inactive') return !c.is_active
    return true
  })

  const sorted = useMemo(() => {
    const arr = [...filtered]
    arr.sort((a, b) => {
      if (sortKey === 'members') {
        return sortDir === 'asc' ? a.member_count - b.member_count : b.member_count - a.member_count
      }
      if (sortKey === 'rating') {
        return sortDir === 'asc' ? a.rating - b.rating : b.rating - a.rating
      }
      return sortDir === 'asc'
        ? (a.username || '').localeCompare(b.username || '')
        : (b.username || '').localeCompare(a.username || '')
    })
    return arr
  }, [filtered, sortKey, sortDir])

  const totalPages = Math.ceil(sorted.length / PAGE_SIZE)
  const paged = sorted.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else {
      setSortKey(key)
      setSortDir(key === 'name' ? 'asc' : 'desc')
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
      <div className="max-w-[1280px] mx-auto space-y-4">
        <Skeleton className="h-16" />
        <Skeleton className="h-16" />
        <Skeleton className="h-56" />
      </div>
    )
  }

  if (isError) {
    return (
      <div className="max-w-[1280px] mx-auto">
        <ScreenHeader
          title="Мои каналы"
          subtitle="Управление вашими Telegram-каналами"
        />
        <EmptyState
          icon="error"
          title="Не удалось загрузить каналы"
          description="Попробуйте обновить страницу"
        />
      </div>
    )
  }

  return (
    <div className="max-w-[1280px] mx-auto">
      <ScreenHeader
        title="Мои каналы"
        subtitle="Управляйте категориями, активностью и сравнением каналов"
        action={
          <div className="flex gap-2">
            <Button variant="secondary" iconLeft="refresh" onClick={() => void refetch()}>
              Обновить
            </Button>
            <Button variant="primary" iconLeft="plus" onClick={() => navigate('/own/channels/add')}>
              Добавить канал
            </Button>
          </div>
        }
      />

      <div
        className="grid gap-3.5 mb-5"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}
      >
        <SummaryTile
          icon="channels"
          tone="accent"
          label="Всего каналов"
          value={String(counts.all)}
          delta={`${counts.active} активных`}
        />
        <SummaryTile
          icon="audience"
          tone="accent2"
          label="Суммарная аудитория"
          value={formatCompactNum(counts.totalMembers)}
          delta="Подписчики по всем каналам"
        />
        <SummaryTile
          icon="verified"
          tone="success"
          label="Активны"
          value={String(counts.active)}
          delta={`${counts.inactive} скрыто`}
        />
        <SummaryTile
          icon="warning"
          tone="warning"
          label="Без категории"
          value={String(counts.withoutCategory)}
          delta="Не видны рекламодателям"
        />
      </div>

      <div className="bg-harbor-card border border-border rounded-xl p-3.5 mb-3.5 flex items-center gap-3 flex-wrap">
        <div className="flex gap-1.5 flex-wrap">
          <FilterPill active={filter === 'all'} onClick={() => handleFilterChange('all')}>
            Все <span className="font-mono tabular-nums text-[11px] opacity-80">{counts.all}</span>
          </FilterPill>
          <FilterPill active={filter === 'active'} tone="success" onClick={() => handleFilterChange('active')}>
            Активные <span className="font-mono tabular-nums text-[11px] opacity-80">{counts.active}</span>
          </FilterPill>
          <FilterPill active={filter === 'inactive'} tone="danger" onClick={() => handleFilterChange('inactive')}>
            Скрытые <span className="font-mono tabular-nums text-[11px] opacity-80">{counts.inactive}</span>
          </FilterPill>
        </div>

        <div className="flex-1" />

        <div className="flex items-center gap-1 text-[12px] text-text-tertiary">
          <span>Сортировка:</span>
          <SortBtn active={sortKey === 'name'} dir={sortDir} onClick={() => toggleSort('name')}>
            Имя
          </SortBtn>
          <SortBtn active={sortKey === 'members'} dir={sortDir} onClick={() => toggleSort('members')}>
            Подписчики
          </SortBtn>
          <SortBtn active={sortKey === 'rating'} dir={sortDir} onClick={() => toggleSort('rating')}>
            Рейтинг
          </SortBtn>
        </div>
      </div>

      {sorted.length === 0 ? (
        <EmptyState
          icon="channels"
          title="Нет каналов"
          description={EMPTY_SUBTITLE[filter]}
          action={
            filter === 'all' || filter === 'active'
              ? { label: 'Добавить канал', onClick: () => navigate('/own/channels/add') }
              : undefined
          }
        />
      ) : (
        <>
          <div
            className="grid gap-3.5 mb-4"
            style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))' }}
          >
            {paged.map((channel) => {
              const categoryLabel = channel.category
                ? CATEGORY_OPTIONS.find((c) => c.key === channel.category)
                : null
              const inCompare = compareIds.has(channel.id)
              const deleting = deletingChannelId === channel.id

              return (
                <div
                  key={channel.id}
                  className="bg-harbor-card border border-border rounded-xl p-4 flex flex-col gap-3"
                >
                  <div className="flex items-start gap-3">
                    <span
                      className={`grid place-items-center w-11 h-11 rounded-[10px] flex-shrink-0 ${
                        channel.is_active
                          ? 'bg-accent-muted text-accent'
                          : 'bg-harbor-elevated text-text-tertiary'
                      }`}
                    >
                      <Icon name="channels" size={18} />
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-display text-[14.5px] font-semibold text-text-primary truncate">
                          @{channel.username}
                        </span>
                        <span
                          className={`text-[10px] font-bold tracking-[0.08em] uppercase py-0.5 px-1.5 rounded ${channel.is_active ? 'bg-success-muted text-success' : 'bg-harbor-elevated text-text-tertiary'}`}
                        >
                          {channel.is_active ? 'Активен' : 'Скрыт'}
                        </span>
                      </div>
                      <div className="text-[12px] text-text-tertiary truncate">{channel.title}</div>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-2 text-center">
                    <StatCell
                      label="Подписчики"
                      value={channel.member_count.toLocaleString('ru-RU')}
                    />
                    <StatCell label="Рейтинг" value={channel.rating.toFixed(1)} />
                    <StatCell
                      label="ER"
                      value={channel.last_er != null ? `${(Number(channel.last_er) * 100).toFixed(1)}%` : '—'}
                    />
                  </div>

                  <div>
                    {categoryLabel ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-accent-muted text-accent">
                        {categoryLabel.emoji} {categoryLabel.label}
                      </span>
                    ) : (
                      <div className="flex flex-col gap-2">
                        <span className="inline-flex items-center gap-1.5 text-[11.5px] text-warning">
                          <Icon name="warning" size={12} /> Без категории — не виден
                        </span>
                        {editingCategoryFor === channel.id ? (
                          <div className="flex flex-wrap gap-1">
                            {CATEGORY_OPTIONS.map((cat) => (
                              <button
                                key={cat.key}
                                className="px-2 py-0.5 rounded text-[11px] bg-harbor-elevated text-text-secondary hover:bg-accent-muted hover:text-accent transition-colors"
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
                          <Button
                            size="sm"
                            variant="secondary"
                            iconLeft="category"
                            onClick={() => setEditingCategoryFor(channel.id)}
                          >
                            Выбрать категорию
                          </Button>
                        )}
                      </div>
                    )}
                  </div>

                  <div className="flex gap-1.5 justify-between border-t border-border pt-3">
                    <button
                      type="button"
                      className={`flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-md text-[12px] font-semibold transition-colors ${
                        inCompare
                          ? 'bg-accent text-accent-text'
                          : compareIds.size >= MAX_COMPARE
                            ? 'bg-harbor-elevated text-text-tertiary cursor-not-allowed'
                            : 'bg-harbor-elevated text-text-secondary hover:bg-accent-muted hover:text-accent'
                      }`}
                      disabled={!inCompare && compareIds.size >= MAX_COMPARE}
                      onClick={() => toggleCompare(channel.id)}
                    >
                      <Icon name="ctr" size={12} />
                      {inCompare ? 'В сравнении' : 'Сравнить'}
                    </button>
                    <Button
                      size="sm"
                      variant="secondary"
                      icon
                      onClick={() => navigate(`/own/channels/${channel.id}/settings`)}
                      title="Настройки"
                    >
                      <Icon name="settings" size={14} />
                    </Button>
                    {channel.is_active ? (
                      <Button
                        size="sm"
                        variant="danger"
                        icon
                        disabled={deleting}
                        loading={deleting}
                        onClick={() => handleDeleteChannel(channel.id, channel.title)}
                        title="Скрыть"
                      >
                        <Icon name="eye-off" size={14} />
                      </Button>
                    ) : (
                      <Button
                        size="sm"
                        variant="primary"
                        icon
                        onClick={() => handleActivateChannel(channel.id, channel.title)}
                        title="Восстановить"
                      >
                        <Icon name="refresh" size={14} />
                      </Button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>

          {counts.withoutCategory > 0 && filter !== 'inactive' && (
            <div className="mb-4">
              <Notification type="warning">
                {counts.withoutCategory} {counts.withoutCategory === 1 ? 'канал' : 'каналов'} без
                категории — они не видны рекламодателям. Выберите категорию на карточке.
              </Notification>
            </div>
          )}

          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-5 py-3.5 px-[18px] rounded-[10px] border border-border bg-harbor-card">
              <Button
                variant="ghost"
                size="sm"
                iconLeft="arrow-left"
                disabled={page === 0}
                onClick={() => setPage((p) => p - 1)}
              >
                Назад
              </Button>
              <div className="flex items-center gap-2.5 text-[12.5px] text-text-secondary">
                <span>Страница</span>
                <span className="font-mono font-semibold text-text-primary py-0.5 px-2.5 rounded-md bg-harbor-elevated border border-border">
                  {page + 1}
                </span>
                <span>из {totalPages}</span>
              </div>
              <Button
                variant="ghost"
                size="sm"
                iconRight="arrow-right"
                disabled={page + 1 >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Вперёд
              </Button>
            </div>
          )}
        </>
      )}

      {compareIds.size >= 2 && (
        <div className="fixed bottom-0 left-0 right-0 z-40 bg-harbor-card border-t border-border shadow-2xl px-4 py-3">
          <div className="max-w-[1280px] mx-auto flex items-center justify-between gap-4">
            <span className="text-sm text-text-secondary flex items-center gap-2">
              <Icon name="ctr" size={14} className="text-accent" />
              Сравниваете{' '}
              <strong className="text-text-primary tabular-nums">{compareIds.size}</strong>{' '}
              {compareIds.size === 1 ? 'канал' : 'канала'}
            </span>
            <div className="flex gap-2">
              <Button variant="ghost" size="sm" onClick={() => setCompareIds(new Set())}>
                Сбросить
              </Button>
              <Button
                variant="primary"
                size="sm"
                iconRight="arrow-right"
                onClick={() => setShowCompare(true)}
              >
                Сравнить
              </Button>
            </div>
          </div>
        </div>
      )}

      {showCompare && compareChannels.length >= 2 && (
        <CompareModal
          channels={compareChannels as ChannelData[]}
          onClose={() => setShowCompare(false)}
        />
      )}
    </div>
  )
}

function formatCompactNum(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return String(n)
}

const toneIconBg: Record<'success' | 'warning' | 'accent' | 'accent2', string> = {
  success: 'bg-success-muted text-success',
  warning: 'bg-warning-muted text-warning',
  accent: 'bg-accent-muted text-accent',
  accent2: 'bg-accent-2-muted text-accent-2',
}

function SummaryTile({
  icon,
  tone,
  label,
  value,
  delta,
}: {
  icon: IconName
  tone: 'success' | 'warning' | 'accent' | 'accent2'
  label: string
  value: string
  delta: string
}) {
  return (
    <div className="bg-harbor-card border border-border rounded-xl p-[18px] flex gap-3.5 items-start">
      <span
        className={`grid place-items-center w-[42px] h-[42px] rounded-[10px] flex-shrink-0 ${toneIconBg[tone]}`}
      >
        <Icon name={icon} size={18} />
      </span>
      <div className="flex-1 min-w-0">
        <div className="text-[11px] font-semibold uppercase tracking-wider text-text-tertiary mb-1">
          {label}
        </div>
        <div className="font-display text-xl font-bold text-text-primary tracking-[-0.02em] tabular-nums truncate">
          {value}
        </div>
        <div className="text-[11.5px] text-text-tertiary mt-0.5 truncate">{delta}</div>
      </div>
    </div>
  )
}

function StatCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-harbor-elevated rounded-md py-2 px-1.5">
      <div className="text-[10px] uppercase tracking-wider text-text-tertiary">{label}</div>
      <div className="font-mono font-semibold tabular-nums text-text-primary text-[13px]">
        {value}
      </div>
    </div>
  )
}

const pillTone: Record<'default' | 'success' | 'danger', { on: string; off: string }> = {
  default: {
    on: 'border-accent bg-accent-muted text-accent',
    off: 'border-border bg-transparent text-text-secondary hover:border-border-active',
  },
  success: {
    on: 'border-success bg-success-muted text-success',
    off: 'border-border bg-transparent text-text-secondary hover:border-border-active',
  },
  danger: {
    on: 'border-danger bg-danger-muted text-danger',
    off: 'border-border bg-transparent text-text-secondary hover:border-border-active',
  },
}

function FilterPill({
  active,
  tone = 'default',
  onClick,
  children,
}: {
  active: boolean
  tone?: 'default' | 'success' | 'danger'
  onClick: () => void
  children: React.ReactNode
}) {
  const cls = active ? pillTone[tone].on : pillTone[tone].off
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded-2xl border transition-all ${cls}`}
    >
      {children}
    </button>
  )
}

function SortBtn({
  active,
  dir,
  onClick,
  children,
}: {
  active: boolean
  dir: SortDir
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center gap-1 px-2 py-1 rounded-md transition-colors ${
        active ? 'bg-harbor-elevated text-text-primary' : 'text-text-secondary hover:text-text-primary'
      }`}
    >
      {children}
      {active && <Icon name={dir === 'asc' ? 'sort-asc' : 'sort-desc'} size={12} />}
      {!active && <Icon name="sort" size={12} className="opacity-60" />}
    </button>
  )
}
