import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Card, Button, Notification, Skeleton } from '@/components/ui'
import AdminNav from '@/components/admin/AdminNav'
import { useUserById, useAddBalance } from '@/hooks/queries/admin/useAdminQueries'
import styles from './AdminUserDetail.module.css'

export default function AdminUserDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const userId = Number(id)

  const { data: user, isLoading, isError } = useUserById(userId)
  const addBalance = useAddBalance()

  const [amount, setAmount] = useState('')
  const [note, setNote] = useState('')
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState('')

  const handleTopUp = () => {
    const parsed = parseFloat(amount)
    if (!parsed || parsed <= 0) {
      setError('Введите корректную сумму')
      return
    }
    setError('')
    setSuccess(false)
    addBalance.mutate(
      { userId, data: { amount: parsed, note } },
      {
        onSuccess: () => {
          setSuccess(true)
          setAmount('')
          setNote('')
        },
        onError: () => setError('Ошибка при зачислении. Попробуйте снова.'),
      }
    )
  }

  return (
    <ScreenShell noPadding className={styles.layout}>
      <aside className={styles.sidebar}>
        <AdminNav />
      </aside>
      <main className={styles.main}>
        <button className={styles.backBtn} onClick={() => navigate('/admin/users')}>
          ← Назад к списку
        </button>

        {isLoading && <Skeleton height={300} />}

        {isError && (
          <Notification type="danger">Не удалось загрузить пользователя</Notification>
        )}

        {user && (
          <>
            <Card className={styles.profileCard}>
              <div className={styles.profileHeader}>
                <div>
                  <div className={styles.userName}>
                    {user.username && (
                      <span className={styles.username}>@{user.username}</span>
                    )}
                    <span className={styles.name}>
                      {user.first_name} {user.last_name ?? ''}
                    </span>
                  </div>
                  <span className={styles.tgId}>TG ID: {user.telegram_id}</span>
                </div>
                <div className={styles.badges}>
                  <span className={styles.badge}>{user.role}</span>
                  <span className={styles.badge}>{user.plan}</span>
                  {user.is_admin && <span className={styles.adminBadge}>Admin</span>}
                </div>
              </div>

              <div className={styles.stats}>
                <div className={styles.statItem}>
                  <span className={styles.statLabel}>Баланс</span>
                  <span className={styles.statValue}>{user.balance_rub} ₽</span>
                </div>
                <div className={styles.statItem}>
                  <span className={styles.statLabel}>Заработано</span>
                  <span className={styles.statValue}>{user.earned_rub} ₽</span>
                </div>
                <div className={styles.statItem}>
                  <span className={styles.statLabel}>Кредиты</span>
                  <span className={styles.statValue}>{user.credits}</span>
                </div>
                <div className={styles.statItem}>
                  <span className={styles.statLabel}>Размещений</span>
                  <span className={styles.statValue}>{user.total_placements}</span>
                </div>
                <div className={styles.statItem}>
                  <span className={styles.statLabel}>Каналов</span>
                  <span className={styles.statValue}>{user.total_channels}</span>
                </div>
                {user.reputation_score !== null && (
                  <div className={styles.statItem}>
                    <span className={styles.statLabel}>Репутация</span>
                    <span className={styles.statValue}>{user.reputation_score?.toFixed(1)}</span>
                  </div>
                )}
              </div>
            </Card>

            <Card className={styles.topupCard}>
              <h2 className={styles.sectionTitle}>Зачислить баланс</h2>

              {success && (
                <Notification type="success">
                  Баланс успешно зачислен
                </Notification>
              )}
              {error && <Notification type="danger">{error}</Notification>}

              <div className={styles.form}>
                <label className={styles.label}>
                  Сумма (₽)
                  <input
                    type="number"
                    className={styles.input}
                    placeholder="Например: 500"
                    value={amount}
                    min="1"
                    max="1000000"
                    onChange={(e) => setAmount(e.target.value)}
                  />
                </label>

                <label className={styles.label}>
                  Примечание (необязательно)
                  <input
                    type="text"
                    className={styles.input}
                    placeholder="Причина зачисления"
                    value={note}
                    maxLength={500}
                    onChange={(e) => setNote(e.target.value)}
                  />
                </label>

                <div className={styles.presets}>
                  {[100, 500, 1000, 5000].map((preset) => (
                    <button
                      key={preset}
                      className={styles.presetBtn}
                      onClick={() => setAmount(String(preset))}
                    >
                      +{preset} ₽
                    </button>
                  ))}
                </div>

                <Button
                  onClick={handleTopUp}
                  disabled={addBalance.isPending || !amount}
                >
                  {addBalance.isPending ? 'Зачисляем...' : 'Зачислить'}
                </Button>
              </div>
            </Card>
          </>
        )}
      </main>
    </ScreenShell>
  )
}
