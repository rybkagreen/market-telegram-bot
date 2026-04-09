import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, Button, Notification, Skeleton } from '@shared/ui'
import { formatCurrency } from '@/lib/constants'
import { useUserById } from '@/hooks/useAdminQueries'
import { api } from '@shared/api/client'

export default function AdminUserDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const userId = Number(id)

  const { data: user, isLoading, isError } = useUserById(userId)

  const [amount, setAmount] = useState('')
  const [note, setNote] = useState('')
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState('')
  const [toppingUp, setToppingUp] = useState(false)

  const handleTopUp = () => {
    const parsed = parseFloat(amount)
    if (!parsed || parsed <= 0) {
      setError('Введите корректную сумму')
      return
    }
    setError('')
    setSuccess(false)
    setToppingUp(true)
    api.post(`admin/users/${userId}/balance`, {
      json: { amount: parsed, note },
    })
      .json()
      .then(() => {
        setSuccess(true)
        setAmount('')
        setNote('')
      })
      .catch(() => setError('Ошибка при зачислении'))
      .finally(() => setToppingUp(false))
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-display font-bold text-text-primary">Пользователь</h1>
        <Button variant="secondary" size="sm" onClick={() => navigate('/admin/users')}>← Назад</Button>
      </div>

      {isLoading && (
        <div className="space-y-4">
          <Skeleton className="h-24" />
          <Skeleton className="h-32" />
        </div>
      )}

      {isError && <Notification type="danger">Не удалось загрузить пользователя</Notification>}

      {user && (
        <>
          {/* Profile */}
          <Card>
            <div className="flex items-start justify-between mb-4">
              <div>
                <p className="text-lg font-semibold text-text-primary">
                  {user.first_name} {user.last_name ?? ''}
                </p>
                {user.username && <p className="text-sm text-text-tertiary">@{user.username}</p>}
                <p className="text-xs text-text-tertiary mt-1">TG ID: {user.telegram_id}</p>
              </div>
              <div className="flex gap-2">
                <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-harbor-elevated text-text-secondary">
                  {user.role}
                </span>
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                  user.plan === 'business' ? 'bg-purple-500/10 text-purple-400' :
                  user.plan === 'pro' ? 'bg-accent-muted text-accent' :
                  user.plan === 'starter' ? 'bg-warning-muted text-warning' :
                  'bg-harbor-elevated text-text-tertiary'
                }`}>
                  {user.plan}
                </span>
                {user.is_admin && (
                  <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-danger-muted text-danger">Admin</span>
                )}
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="text-center p-3 bg-accent-muted rounded-lg">
                <p className="text-xl font-bold text-accent">{formatCurrency(user.balance_rub)}</p>
                <p className="text-xs text-text-tertiary mt-1">Баланс</p>
              </div>
              <div className="text-center p-3 bg-success-muted rounded-lg">
                <p className="text-xl font-bold text-success">{formatCurrency(user.earned_rub)}</p>
                <p className="text-xs text-text-tertiary mt-1">Заработано</p>
              </div>
              <div className="text-center p-3 bg-harbor-elevated rounded-lg">
                <p className="text-xl font-bold text-text-primary">{user.balance_rub}</p>
                <p className="text-xs text-text-tertiary mt-1">Баланс ₽</p>
              </div>
              <div className="text-center p-3 bg-harbor-elevated rounded-lg">
                <p className="text-xl font-bold text-text-primary">{user.reputation_score?.toFixed(1) ?? '—'}</p>
                <p className="text-xs text-text-tertiary mt-1">Репутация</p>
              </div>
            </div>
          </Card>

          {/* Top-up */}
          <Card title="Зачислить баланс">
            {success && <Notification type="success">Баланс зачислён</Notification>}
            {error && <Notification type="danger">{error}</Notification>}

            <div className="space-y-3 mt-3">
              <input
                className="w-full px-4 py-2.5 bg-harbor-elevated border border-border rounded-md text-text-primary placeholder:text-text-tertiary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/30 text-sm"
                type="number"
                placeholder="Сумма (₽)"
                value={amount}
                min={1}
                onChange={(e) => setAmount(e.target.value)}
              />
              <input
                className="w-full px-4 py-2.5 bg-harbor-elevated border border-border rounded-md text-text-primary placeholder:text-text-tertiary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/30 text-sm"
                type="text"
                placeholder="Примечание (необязательно)"
                value={note}
                maxLength={500}
                onChange={(e) => setNote(e.target.value)}
              />
              <div className="flex gap-2">
                {[100, 500, 1000, 5000].map((preset) => (
                  <button
                    key={preset}
                    className="px-3 py-1.5 rounded-full text-sm font-medium border border-border bg-harbor-elevated text-text-secondary hover:border-accent hover:text-accent transition-all"
                    onClick={() => setAmount(String(preset))}
                  >
                    +{preset} ₽
                  </button>
                ))}
              </div>
              <Button variant="primary" fullWidth loading={toppingUp} disabled={!amount} onClick={handleTopUp}>
                {toppingUp ? 'Зачисление...' : 'Зачислить'}
              </Button>
            </div>
          </Card>
        </>
      )}
    </div>
  )
}
