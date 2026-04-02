/**
 * AdminUsersList — List of all users
 * 
 * Features:
 * - Users table with pagination
 * - Search by username
 * - Role filter
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useUsersList } from '@/hooks/queries/admin/useAdminQueries'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Card, Button, Skeleton, Notification } from '@/components/ui'
import AdminNav from '@/components/admin/AdminNav'
import styles from './AdminUsersList.module.css'

type RoleFilter = 'all' | 'advertiser' | 'owner' | 'both'

export default function AdminUsersList() {
  const navigate = useNavigate()
  const [roleFilter, setRoleFilter] = useState<RoleFilter>('all')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(0)
  const limit = 50

  const { data, isLoading, error } = useUsersList({
    role: roleFilter === 'all' ? undefined : roleFilter,
    limit,
    offset: page * limit,
  })

  const filteredData = data ? {
    ...data,
    items: data.items.filter(user => 
      !search || 
      (user.username && user.username.toLowerCase().includes(search.toLowerCase())) ||
      user.first_name.toLowerCase().includes(search.toLowerCase())
    ),
  } : data

  if (isLoading) {
    return (
      <ScreenShell>
        <Skeleton height={300} />
      </ScreenShell>
    )
  }

  if (error || !filteredData) {
    return (
      <ScreenShell>
        <Notification type="danger">Failed to load users</Notification>
      </ScreenShell>
    )
  }

  return (
    <ScreenShell noPadding className={styles.layout}>
      <aside className={styles.sidebar}>
        <AdminNav />
      </aside>
      <main className={styles.main}>
        <div className={styles.header}>
          <h1 className={styles.title}>Users</h1>
          
          <div className={styles.controls}>
            <input
              type="text"
              className={styles.searchInput}
              placeholder="Search by username or name..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            
            <div className={styles.filters}>
              {(['all', 'advertiser', 'owner', 'both'] as RoleFilter[]).map((role) => (
                <button
                  key={role}
                  className={`${styles.filterBtn} ${roleFilter === role ? styles.active : ''}`}
                  onClick={() => {
                    setRoleFilter(role)
                    setPage(0)
                  }}
                >
                  {role === 'all' ? 'All' : role}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className={styles.list}>
          {filteredData.items.length === 0 ? (
            <Card>
              <div className={styles.empty}>No users found</div>
            </Card>
          ) : (
            filteredData.items.map((user) => (
              <Card key={user.id} className={styles.userCard} onClick={() => navigate(`/admin/users/${user.id}`)}>
                <div className={styles.userHeader}>
                  <div className={styles.userInfo}>
                    <div className={styles.userName}>
                      {user.username && <span className={styles.username}>@{user.username}</span>}
                      <span className={styles.name}>{user.first_name} {user.last_name}</span>
                    </div>
                    <span className={styles.tgId}>ID: {user.telegram_id}</span>
                  </div>
                  <div className={styles.userMeta}>
                    <span className={styles.badge}>{user.role}</span>
                    <span className={styles.badge}>{user.plan}</span>
                    <span className={styles.balance}>{user.balance_rub} ₽</span>
                    {user.is_admin ? (
                      <span className={styles.adminBadge}>Admin</span>
                    ) : (
                      <span className={styles.userBadge}>User</span>
                    )}
                  </div>
                </div>
              </Card>
            ))
          )}
        </div>

        {/* Pagination */}
        {filteredData.total > limit && (
          <div className={styles.pagination}>
            <Button
              size="sm"
              variant="secondary"
              disabled={page === 0}
              onClick={() => setPage(page - 1)}
            >
              Previous
            </Button>
            <span className={styles.pageInfo}>
              Page {page + 1} of {Math.ceil(filteredData.total / limit)}
            </span>
            <Button
              size="sm"
              variant="secondary"
              disabled={(page + 1) * limit >= filteredData.total}
              onClick={() => setPage(page + 1)}
            >
              Next
            </Button>
          </div>
        )}
      </main>
    </ScreenShell>
  )
}
