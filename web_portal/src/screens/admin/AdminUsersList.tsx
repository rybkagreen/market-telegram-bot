import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Button, Skeleton, Notification } from '@shared/ui'
import { useUsersList, useUpdateAdminUser } from '@/hooks/useAdminQueries'
import { formatCurrency } from '@/lib/constants'

type RoleFilter = 'all' | 'advertiser' | 'owner' | 'both'

const ROLES = ['advertiser', 'owner', 'both']
const PLANS = ['free', 'starter', 'pro', 'business']

const ROLE_LABELS: Record<RoleFilter, string> = {
  all: 'Все',
  advertiser: 'Рекл.',
  owner: 'Владелец',
  both: 'Обе',
}

export default function AdminUsersList() {
  const navigate = useNavigate()
  const [roleFilter, setRoleFilter] = useState<RoleFilter>('all')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(0)
  const limit = 50

  // Bulk selection state
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [bulkRole, setBulkRole] = useState('')
  const [bulkPlan, setBulkPlan] = useState('')

  const { data, isLoading, error } = useUsersList({
    role: roleFilter === 'all' ? undefined : roleFilter,
    limit,
    offset: page * limit,
  })
  const updateUser = useUpdateAdminUser()

  // Client-side search filter
  const filteredItems = data?.items.filter((user) =>
    !search ||
    (user.username && user.username.toLowerCase().includes(search.toLowerCase())) ||
    user.first_name.toLowerCase().includes(search.toLowerCase())
  ) ?? []

  const allPageIds = filteredItems.map((u) => u.id)
  const allSelected = allPageIds.length > 0 && allPageIds.every((id) => selectedIds.has(id))

  const toggleSelectAll = () => {
    if (allSelected) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(allPageIds))
    }
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
      })
    )
    await Promise.allSettled(updates)
    setSelectedIds(new Set())
    setBulkRole('')
    setBulkPlan('')
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-12" />
        <Skeleton className="h-96" />
      </div>
    )
  }

  if (error || !data) {
    return <Notification type="danger">Не удалось загрузить список пользователей.</Notification>
  }

  return (
    <div className="space-y-6">
      {/* Page title + controls */}
      <div>
        <h1 className="text-2xl font-display font-bold text-text-primary">Пользователи</h1>
        <p className="text-text-secondary mt-1">Всего: {data.total}</p>
      </div>

      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row gap-3">
        <input
          type="text"
          className="flex-1 px-3 py-2 rounded-md border border-border-active bg-harbor-elevated text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent"
          placeholder="Поиск по имени или @username..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(0); setSelectedIds(new Set()) }}
        />
        <div className="flex gap-2">
          {(['all', 'advertiser', 'owner', 'both'] as RoleFilter[]).map((role) => (
            <button
              key={role}
              className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                roleFilter === role
                  ? 'bg-accent text-accent-text'
                  : 'bg-harbor-elevated text-text-secondary hover:text-text-primary'
              }`}
              onClick={() => { setRoleFilter(role); setPage(0); setSelectedIds(new Set()) }}
            >
              {ROLE_LABELS[role]}
            </button>
          ))}
        </div>
      </div>

      {/* Bulk action toolbar */}
      {selectedIds.size > 0 && (
        <div className="bg-accent-muted border border-accent/30 rounded-lg px-4 py-3 flex flex-wrap items-center gap-3">
          <span className="text-sm font-medium text-accent">
            Выбрано: {selectedIds.size}
          </span>
          <div className="flex items-center gap-2 flex-wrap">
            <select
              className="px-2 py-1.5 rounded-md border border-border-active bg-harbor-elevated text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-accent"
              value={bulkRole}
              onChange={(e) => setBulkRole(e.target.value)}
            >
              <option value="">— Роль —</option>
              {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
            <select
              className="px-2 py-1.5 rounded-md border border-border-active bg-harbor-elevated text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-accent"
              value={bulkPlan}
              onChange={(e) => setBulkPlan(e.target.value)}
            >
              <option value="">— Тариф —</option>
              {PLANS.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
            <Button
              size="sm"
              variant="primary"
              disabled={(!bulkRole && !bulkPlan) || updateUser.isPending}
              onClick={applyBulkAction}
            >
              {updateUser.isPending ? '⏳ Применяем...' : '✅ Применить'}
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setSelectedIds(new Set())}>
              ✕ Снять выбор
            </Button>
          </div>
        </div>
      )}

      {/* Users table */}
      <Card className="p-0 overflow-hidden">
        {filteredItems.length === 0 ? (
          <div className="px-5 py-8 text-center text-text-secondary">Пользователи не найдены</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-harbor-elevated">
                <tr>
                  <th className="px-4 py-3 w-10">
                    <input
                      type="checkbox"
                      className="rounded border-border-active accent-accent"
                      checked={allSelected}
                      onChange={toggleSelectAll}
                    />
                  </th>
                  <th className="text-left px-4 py-3 text-text-secondary font-medium">Имя</th>
                  <th className="text-left px-4 py-3 text-text-secondary font-medium hidden md:table-cell">Роль</th>
                  <th className="text-left px-4 py-3 text-text-secondary font-medium hidden lg:table-cell">Тариф</th>
                  <th className="text-right px-4 py-3 text-text-secondary font-medium hidden sm:table-cell">Баланс</th>
                  <th className="text-right px-4 py-3 text-text-secondary font-medium">Репутация</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filteredItems.map((user) => (
                  <tr
                    key={user.id}
                    className={`hover:bg-harbor-elevated/50 transition-colors ${
                      selectedIds.has(user.id) ? 'bg-accent-muted/30' : ''
                    }`}
                  >
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        className="rounded border-border-active accent-accent"
                        checked={selectedIds.has(user.id)}
                        onChange={() => toggleSelect(user.id)}
                        onClick={(e) => e.stopPropagation()}
                      />
                    </td>
                    <td
                      className="px-4 py-3 cursor-pointer"
                      onClick={() => navigate(`/admin/users/${user.id}`)}
                    >
                      <p className="font-medium text-text-primary">{user.first_name} {user.last_name}</p>
                      {user.username && <p className="text-xs text-text-tertiary">@{user.username}</p>}
                    </td>
                    <td className="px-4 py-3 hidden md:table-cell">
                      <span className="text-text-secondary capitalize">{user.role}</span>
                    </td>
                    <td className="px-4 py-3 hidden lg:table-cell">
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                        user.plan === 'business' ? 'bg-purple-500/10 text-purple-400' :
                        user.plan === 'pro' ? 'bg-accent-muted text-accent' :
                        user.plan === 'starter' ? 'bg-warning-muted text-warning' :
                        'bg-harbor-elevated text-text-tertiary'
                      }`}>
                        {user.plan}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-text-primary hidden sm:table-cell">
                      {formatCurrency(user.balance_rub)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className={user.reputation_score && user.reputation_score >= 4 ? 'text-success' : 'text-text-secondary'}>
                        {user.reputation_score?.toFixed(1) ?? '—'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Pagination */}
      {data.total > limit && (
        <div className="flex items-center justify-between">
          <Button
            size="sm"
            variant="secondary"
            disabled={page === 0}
            onClick={() => { setPage(page - 1); setSelectedIds(new Set()) }}
          >
            ← Назад
          </Button>
          <span className="text-sm text-text-secondary">
            Страница {page + 1} из {Math.ceil(data.total / limit)} ({data.total} всего)
          </span>
          <Button
            size="sm"
            variant="secondary"
            disabled={(page + 1) * limit >= data.total}
            onClick={() => { setPage(page + 1); setSelectedIds(new Set()) }}
          >
            Далее →
          </Button>
        </div>
      )}
    </div>
  )
}
