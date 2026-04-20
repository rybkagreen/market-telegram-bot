import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Button,
  Notification,
  Skeleton,
  Icon,
  ScreenHeader,
} from '@shared/ui'
import type { IconName } from '@shared/ui'
import { formatCurrency } from '@/lib/constants'
import {
  useUserById,
  useCreatePlatformCredit,
  useCreateGamificationBonus,
  useTopupUserBalance,
} from '@/hooks/useAdminQueries'

const BALANCE_PRESETS = [100, 500, 1000, 5000]

export default function AdminUserDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const userId = Number(id)

  const { data: user, isLoading, isError } = useUserById(userId)

  const [amount, setAmount] = useState('')
  const [note, setNote] = useState('')
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState('')
  const topupBalance = useTopupUserBalance()

  const [creditAmount, setCreditAmount] = useState('')
  const [creditComment, setCreditComment] = useState('')
  const [creditFeedback, setCreditFeedback] = useState<
    { type: 'success' | 'danger'; text: string } | null
  >(null)
  const platformCredit = useCreatePlatformCredit()

  const [bonusAmount, setBonusAmount] = useState('')
  const [bonusXp, setBonusXp] = useState('')
  const [bonusComment, setBonusComment] = useState('')
  const [bonusFeedback, setBonusFeedback] = useState<
    { type: 'success' | 'danger'; text: string } | null
  >(null)
  const gamificationBonus = useCreateGamificationBonus()

  const handleTopUp = () => {
    const parsed = parseFloat(amount)
    if (!parsed || parsed <= 0) {
      setError('Введите корректную сумму')
      return
    }
    setError('')
    setSuccess(false)
    topupBalance.mutate(
      { userId, amount: parsed, note },
      {
        onSuccess: () => {
          setSuccess(true)
          setAmount('')
          setNote('')
        },
        onError: () => setError('Ошибка при зачислении'),
      },
    )
  }

  const handlePlatformCredit = () => {
    const parsed = parseFloat(creditAmount)
    if (!parsed || parsed <= 0) {
      setCreditFeedback({ type: 'danger', text: 'Введите корректную сумму' })
      return
    }
    setCreditFeedback(null)
    platformCredit.mutate(
      { user_id: userId, amount: parsed, comment: creditComment },
      {
        onSuccess: (data) => {
          setCreditFeedback({
            type: 'success',
            text: `Начислено ${parsed} ₽. Новый баланс пользователя: ${data.new_user_balance} ₽`,
          })
          setCreditAmount('')
          setCreditComment('')
        },
        onError: (e: unknown) => {
          const message = e instanceof Error ? e.message : 'Ошибка зачисления'
          setCreditFeedback({ type: 'danger', text: message })
        },
      },
    )
  }

  const handleGamificationBonus = () => {
    const parsedAmount = bonusAmount ? parseFloat(bonusAmount) : 0
    const parsedXp = bonusXp ? parseInt(bonusXp, 10) : 0
    if (!parsedAmount && !parsedXp) {
      setBonusFeedback({ type: 'danger', text: 'Укажите сумму или XP' })
      return
    }
    setBonusFeedback(null)
    gamificationBonus.mutate(
      { user_id: userId, amount: parsedAmount, xp_amount: parsedXp, comment: bonusComment },
      {
        onSuccess: (data) => {
          setBonusFeedback({
            type: 'success',
            text: `Бонус начислен. Баланс: ${data.new_user_balance} ₽, XP: ${data.new_user_xp}`,
          })
          setBonusAmount('')
          setBonusXp('')
          setBonusComment('')
        },
        onError: (e: unknown) => {
          const message = e instanceof Error ? e.message : 'Ошибка начисления бонуса'
          setBonusFeedback({ type: 'danger', text: message })
        },
      },
    )
  }

  return (
    <div className="max-w-[1080px] mx-auto">
      <ScreenHeader
        crumbs={['Администратор', 'Пользователи', `#${userId}`]}
        title="Профиль пользователя"
        subtitle={
          user
            ? `${user.first_name} ${user.last_name ?? ''}${user.username ? ` · @${user.username}` : ''}`
            : undefined
        }
        action={
          <Button
            variant="secondary"
            iconLeft="arrow-left"
            onClick={() => navigate('/admin/users')}
          >
            К списку
          </Button>
        }
      />

      {isLoading && (
        <div className="space-y-4">
          <Skeleton className="h-28" />
          <Skeleton className="h-40" />
        </div>
      )}

      {isError && <Notification type="danger">Не удалось загрузить пользователя</Notification>}

      {user && (
        <>
          <div className="bg-harbor-card border border-border rounded-xl p-5 mb-5 relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-[3px] bg-gradient-to-r from-accent to-accent-2" />
            <div className="flex items-start gap-4 flex-wrap">
              <span className="grid place-items-center w-14 h-14 rounded-[14px] bg-accent-muted text-accent font-display text-[22px] font-bold flex-shrink-0">
                {user.first_name[0]?.toUpperCase() ?? '#'}
              </span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-display text-[18px] font-semibold text-text-primary">
                    {user.first_name} {user.last_name ?? ''}
                  </span>
                  <span
                    className={`text-[10.5px] font-bold tracking-[0.08em] uppercase py-0.5 px-1.5 rounded ${
                      user.plan === 'business'
                        ? 'bg-accent-2-muted text-accent-2'
                        : user.plan === 'pro'
                          ? 'bg-accent-muted text-accent'
                          : user.plan === 'starter'
                            ? 'bg-warning-muted text-warning'
                            : 'bg-harbor-elevated text-text-tertiary'
                    }`}
                  >
                    {user.plan}
                  </span>
                  {user.is_admin && (
                    <span className="text-[10.5px] font-bold tracking-[0.08em] uppercase py-0.5 px-1.5 rounded bg-danger-muted text-danger">
                      Admin
                    </span>
                  )}
                </div>
                <div className="text-[12.5px] text-text-tertiary mt-0.5">
                  {user.username ? `@${user.username} · ` : ''}TG ID {user.telegram_id}
                </div>
              </div>
            </div>

            <div
              className="grid gap-3 mt-4"
              style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))' }}
            >
              <StatTile
                icon="wallet"
                tone="accent"
                label="Баланс"
                value={formatCurrency(user.balance_rub)}
              />
              <StatTile
                icon="deposit"
                tone="success"
                label="Заработано"
                value={formatCurrency(user.earned_rub)}
              />
              <StatTile
                icon="star"
                tone="warning"
                label="Репутация"
                value={user.reputation_score?.toFixed(1) ?? '—'}
              />
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            <SectionCard icon="deposit" title="Зачислить баланс">
              {success && <Notification type="success">Баланс зачислён</Notification>}
              {error && <Notification type="danger">{error}</Notification>}
              <div className="space-y-3 mt-3">
                <AdminInput
                  type="number"
                  placeholder="Сумма (₽)"
                  value={amount}
                  onChange={setAmount}
                />
                <AdminInput
                  placeholder="Примечание (необязательно)"
                  value={note}
                  onChange={setNote}
                  maxLength={500}
                />
                <div className="flex gap-1.5 flex-wrap">
                  {BALANCE_PRESETS.map((p) => (
                    <button
                      key={p}
                      className="px-2.5 py-1 rounded-full text-[11.5px] font-semibold border border-border bg-harbor-elevated text-text-secondary hover:border-accent hover:text-accent transition-all"
                      onClick={() => setAmount(String(p))}
                    >
                      +{p} ₽
                    </button>
                  ))}
                </div>
                <Button
                  variant="primary"
                  fullWidth
                  iconLeft="deposit"
                  loading={topupBalance.isPending}
                  disabled={!amount || topupBalance.isPending}
                  onClick={handleTopUp}
                >
                  Зачислить
                </Button>
              </div>
            </SectionCard>

            <SectionCard icon="coin" title="Кредит из доходов">
              {creditFeedback && <Notification type={creditFeedback.type}>{creditFeedback.text}</Notification>}
              <div className="space-y-3 mt-3">
                <AdminInput
                  type="number"
                  placeholder="Сумма (₽)"
                  value={creditAmount}
                  onChange={setCreditAmount}
                />
                <AdminInput
                  placeholder="Комментарий (причина, тикет)"
                  value={creditComment}
                  onChange={setCreditComment}
                  maxLength={500}
                />
                <Button
                  variant="primary"
                  fullWidth
                  iconLeft="coin"
                  loading={platformCredit.isPending}
                  disabled={!creditAmount || platformCredit.isPending}
                  onClick={handlePlatformCredit}
                >
                  Выдать кредиты
                </Button>
              </div>
            </SectionCard>

            <SectionCard icon="star" title="Геймификация">
              {bonusFeedback && <Notification type={bonusFeedback.type}>{bonusFeedback.text}</Notification>}
              <div className="space-y-3 mt-3">
                <div className="grid grid-cols-2 gap-2">
                  <AdminInput
                    type="number"
                    placeholder="₽"
                    value={bonusAmount}
                    onChange={setBonusAmount}
                  />
                  <AdminInput
                    type="number"
                    placeholder="XP"
                    value={bonusXp}
                    onChange={setBonusXp}
                  />
                </div>
                <AdminInput
                  placeholder="Комментарий (событие, акция)"
                  value={bonusComment}
                  onChange={setBonusComment}
                  maxLength={500}
                />
                <Button
                  variant="primary"
                  fullWidth
                  iconLeft="zap"
                  loading={gamificationBonus.isPending}
                  disabled={(!bonusAmount && !bonusXp) || gamificationBonus.isPending}
                  onClick={handleGamificationBonus}
                >
                  Зачислить бонус
                </Button>
              </div>
            </SectionCard>
          </div>
        </>
      )}
    </div>
  )
}

const toneIconBg: Record<'success' | 'warning' | 'accent', string> = {
  success: 'bg-success-muted text-success',
  warning: 'bg-warning-muted text-warning',
  accent: 'bg-accent-muted text-accent',
}

function StatTile({
  icon,
  tone,
  label,
  value,
}: {
  icon: IconName
  tone: 'success' | 'warning' | 'accent'
  label: string
  value: string
}) {
  return (
    <div className="bg-harbor-secondary border border-border rounded-[10px] p-3 flex gap-3 items-center">
      <span className={`grid place-items-center w-9 h-9 rounded-md flex-shrink-0 ${toneIconBg[tone]}`}>
        <Icon name={icon} size={15} />
      </span>
      <div className="min-w-0">
        <div className="text-[10.5px] uppercase tracking-wider text-text-tertiary">{label}</div>
        <div className="font-mono tabular-nums font-semibold text-text-primary text-[14px] truncate">
          {value}
        </div>
      </div>
    </div>
  )
}

function SectionCard({
  icon,
  title,
  children,
}: {
  icon: IconName
  title: string
  children: React.ReactNode
}) {
  return (
    <div className="bg-harbor-card border border-border rounded-xl overflow-hidden">
      <div className="px-5 py-3 border-b border-border flex items-center gap-2">
        <Icon name={icon} size={14} className="text-text-tertiary" />
        <span className="font-display text-[14px] font-semibold text-text-primary">{title}</span>
      </div>
      <div className="p-5">{children}</div>
    </div>
  )
}

function AdminInput({
  type = 'text',
  placeholder,
  value,
  onChange,
  maxLength,
}: {
  type?: 'text' | 'number'
  placeholder: string
  value: string
  onChange: (v: string) => void
  maxLength?: number
}) {
  return (
    <input
      className="w-full px-3 py-2 bg-harbor-elevated border border-border rounded-md text-text-primary placeholder:text-text-tertiary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/30 text-sm"
      type={type}
      placeholder={placeholder}
      value={value}
      maxLength={maxLength}
      onChange={(e) => onChange(e.target.value)}
    />
  )
}
