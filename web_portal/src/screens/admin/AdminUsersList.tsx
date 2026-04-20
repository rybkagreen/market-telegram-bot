import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Button,
  Skeleton,
  Notification,
  Icon,
  ScreenHeader,
  EmptyState,
} from '@shared/ui'
import { useUsersList, useUpdateAdminUser } from '@/hooks/useAdminQueries'
import { formatCurrency } from '@/lib/constants'

type RoleFilter = 'all' | 'advertiser' | 'owner' | 'both'

const ROLES = ['advertiser', 'owner', 'both']
const PLANS = ['free', 'starter', 'pro', 'business']

const ROLE_FILTERS: { key: RoleFilter; label: string }[] = [
  { key: 'all', label: 'Все' },
  { key: 'advertiser', label: 'Рекламодатели' },
  { key: 'owner', label: 'Владельцы' },
  { key: 'both', label: 'Обе роли' },
]

export default function AdminUsersList() {
  const navigate = useNavigate()
  const [roleFilter, setRoleFilter] = useState<RoleFilter>('all')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(0)
  const limit = 50

  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [bulkRole, setBulkRole] = useState('')
  const [bulkPlan, setBulkPlan] = useState('')

  const { data, isLoading, error } = useUsersList({
    role: roleFilter === 'all' ? undefined : roleFilter,
    limit,
    offset: page * limit,
  })
  const updateUser = useUpdateAdminUser()

  const filteredItems =
    data?.items.filter(
      (user) =>
        !search ||
        (user.username && user.username.toLowerCase().includes(search.toLowerCase())) ||
        user.first_name.toLowerCase().includes(search.toLowerCase()),
    ) ?? []

  const allPageIds = filteredItems.map((u) => u.id)
  const allSelected = allPageIds.length > 0 && allPageIds.every((id) => selectedIds.has(id))

  const toggleSelectAll = () => {
    if (allSelected) setSelectedIds(new Set())
    else setSelectedIds(new Set(allPageIds))
  }

  const toggleSelect = (id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const applyBulkAction = async () => {
    if (!bulkRole && !bulkPlan) return
    const ids = Array.from(selectedIds)
    const updates = ids.map((userId) =>
      updateUser.mutateAsync({
        userId,
        data: {
          ...(bulkRole ? { role: bulkRole } : {}),
          ...(bulkPlan ? { plan: bulkPlan } : {}),
        },
      }),
    )
    await Promise.allSettled(updates)
    setSelectedIds(new Set())
    setBulkRole('')
    setBulkPlan('')
  }

  if (isLoading) {
    return (
      <div className="max-w-[1280px] mx-auto space-y-4">
        <Skeleton className="h-16" />
        <Skeleton className="h-96" />
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="max-w-[1280px] mx-auto">
        <Notification type="danger">Не удалось загрузить список пользователей.</Notification>
      </div>
    )
  }

  return (
    <div className="max-w-[1280px] mx-auto">
      <ScreenHeader
        title="Пользователи"
        subtitle={`Всего: ${data.total} · управление ролями, тарифами, балансами`}
      />

      <div className="bg-harbor-card border border-border rounded-xl p-3.5 mb-3.5 flex items-center gap-3 flex-wrap">
        <div className="flex-1 min-w-[260px] flex items-center gap-2 px-3 py-2 rounded-lg bg-harbor-elevated border border-border">
          <Icon name="search" size={15} className="text-text-tertiary" />
          <input
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setPage(0)
              setSelectedIds(new Set())
            }}
            placeholder="Поиск по имени или @username"
            className="flex-1 bg-transparent border-0 outline-none text-text-primary text-[13px] placeholder:text-text-tertiary"
          />
        </div>

        <div className="flex gap-1.5 flex-wrap">
          {ROLE_FILTERS.map((f) => {
            const on = roleFilter === f.key
            return (
              <button
                key={f.key}
                type="button"
                onClick={() => {
                  setRoleFilter(f.key)
                  setPage(0)
                  setSelectedIds(new Set())
                }}
                className={`inline-flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded-2xl border transition-all ${
                  on
                    ? 'border-accent bg-accent-muted text-accent'
                    : 'border-border bg-transparent text-text-secondary hover:border-border-active'
                }`}
              >
                {f.label}
              </button>
            )
          })}
        </div>
      </div>

      {selectedIds.size > 0 && (
        <div className="bg-accent-muted/60 border border-accent/30 rounded-xl px-4 py-3 mb-3.5 flex flex-wrap items-center gap-3">
          <span className="inline-flex items-center gap-1.5 text-[13px] font-semibold text-accent">
            <Icon name="check" size={13} />
            Выбрано: {selectedIds.size}
          </span>
          <div className="flex items-center gap-2 flex-wrap">
            <select
              className="px-3 py-2 rounded-md border border-border bg-harbor-elevated text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
              value={bulkRole}
              onChange={(e) => setBulkRole(e.target.value)}
            >
              <option value="">— Роль —</option>
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
            <select
              className="px-3 py-2 rounded-md border border-border bg-harbor-elevated text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
              value={bulkPlan}
              onChange={(e) => setBulkPlan(e.target.value)}
            >
              <option value="">— Тариф —</option>
              {PLANS.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
            <Button
              size="sm"
              variant="primary"
              iconLeft="check"
              disabled={(!bulkRole && !bulkPlan) || updateUser.isPending}
              loading={updateUser.isPending}
              onClick={applyBulkAction}
            >
              Применить
            </Button>
            <Button size="sm" variant="ghost" iconLeft="close" onClick={() => setSelectedIds(new Set())}>
              Снять выбор
            </Button>
          </div>
        </div>
      )}

      {filteredItems.length === 0 ? (
        <EmptyState
          icon="users"
          title="Пользователи не найдены"
          description="Попробуйте изменить фильтр роли или строку поиска."
        />
      ) : (
        <div className="bg-harbor-card border border-border rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-harbor-secondary">
                <tr className="text-[11px] uppercase tracking-[0.08em] text-text-tertiary font-semibold">
                  <th className="px-4 py-2.5 w-10">
                    <input
                      type="checkbox"
                      className="rounded border-border accent-accent"
                      checked={allSelected}
                      onChange={toggleSelectAll}
                    />
                  </th>
                  <th className="text-left px-4 py-2.5">Имя</th>
                  <th className="text-left px-4 py-2.5 hidden md:table-cell">Тариф</th>
                  <th className="text-right px-4 py-2.5 hidden sm:table-cell">Баланс</th>
                  <th className="text-right px-4 py-2.5">Репутация</th>
                  <th className="w-8" />
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filteredItems.map((user) => {
                  const selected = selectedIds.has(user.id)
                  return (
                    <tr
                      key={user.id}
                      className={`hover:bg-harbor-elevated/40 transition-colors ${selected ? 'bg-accent-muted/30' : ''}`}
                    >
                      <td className="px-4 py-3">
                        <input
                          type="checkbox"
                          className="rounded border-border accent-accent"
                          checked={selected}
                          onChange={() => toggleSelect(user.id)}
                          onClick={(e) => e.stopPropagation()}
                        />
                      </td>
                      <td
                        className="px-4 py-3 cursor-pointer"
                        onClick={() => navigate(`/admin/users/${user.id}`)}
                      >
                        <p className="font-medium text-text-primary">
                          {user.first_name} {user.last_name}
                        </p>
                        {user.username && (
                          <p className="text-xs text-text-tertiary">@{user.username}</p>
                        )}
                      </td>
                      <td className="px-4 py-3 hidden md:table-cell">
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-harbor-elevated text-text-secondary capitalize">
                          {user.plan}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right font-mono tabular-nums text-text-primary hidden sm:table-cell">
                        {formatCurrency(user.balance_rub)}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span
                          className={`font-mono tabular-nums font-semibold ${user.reputation_score && user.reputation_score >= 4 ? 'text-success' : 'text-text-secondary'}`}
                        >
                          {user.reputation_score?.toFixed(1) ?? '—'}
                        </span>
                      </td>
                      <td className="px-2 py-3 text-right">
                        <button
                          type="button"
                          onClick={() => navigate(`/admin/users/${user.id}`)}
                          className="text-text-tertiary hover:text-accent"
                          aria-label="Открыть"
                        >
                          <Icon name="chevron-right" size={14} />
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {data.total > limit && (
        <div className="flex items-center justify-between mt-5 py-3.5 px-[18px] rounded-[10px] border border-border bg-harbor-card">
          <Button
            size="sm"
            variant="ghost"
            iconLeft="arrow-left"
            disabled={page === 0}
            onClick={() => {
              setPage(page - 1)
              setSelectedIds(new Set())
            }}
          >
            Назад
          </Button>
          <div className="flex items-center gap-2.5 text-[12.5px] text-text-secondary">
            <span>Страница</span>
            <span className="font-mono font-semibold text-text-primary py-0.5 px-2.5 rounded-md bg-harbor-elevated border border-border">
              {page + 1}
            </span>
            <span>из {Math.ceil(data.total / limit)}</span>
          </div>
          <Button
            size="sm"
            variant="ghost"
            iconRight="arrow-right"
            disabled={(page + 1) * limit >= data.total}
            onClick={() => {
              setPage(page + 1)
              setSelectedIds(new Set())
            }}
          >
            Вперёд
          </Button>
        </div>
      )}
    </div>
  )
}
