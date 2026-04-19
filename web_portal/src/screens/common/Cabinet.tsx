import { Card, Notification, Skeleton, MenuButton } from '@shared/ui'
import { formatCurrency, PLAN_INFO } from '@/lib/constants'
import { useMe, useMyStats } from '@/hooks/queries'

function getScoreColor(score: number): string {
  if (score >= 4) return 'bg-success'
  if (score >= 3) return 'bg-warning'
  return 'bg-danger'
}

export default function Cabinet() {
  const { data: user, isLoading: userLoading, isError: userError } = useMe()
  const { data: stats, isLoading: statsLoading } = useMyStats()

  if (userLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-20" />
        <Skeleton className="h-40" />
      </div>
    )
  }

  if (userError) {
    return <Notification type="danger">Не удалось загрузить данные</Notification>
  }

  const plan = user ? PLAN_INFO[user.plan] : null
  const advertiserScore = stats?.reputation?.advertiser_score ?? 5.0
  const ownerScore = stats?.reputation?.owner_score ?? 5.0

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-display font-bold text-text-primary">Кабинет</h1>

      {/* Balances */}
      <Card title="Ваши балансы">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="text-center p-4 bg-accent-muted rounded-lg">
            <p className="text-2xl font-bold text-accent">
              {user ? formatCurrency(user.balance_rub) : '—'}
            </p>
            <p className="text-sm text-text-secondary mt-1">💳 Баланс рекл.</p>
          </div>
          <div className="text-center p-4 bg-success-muted rounded-lg">
            <p className="text-2xl font-bold text-success">
              {user ? formatCurrency(user.earned_rub) : '—'}
            </p>
            <p className="text-sm text-text-secondary mt-1">💰 Заработок</p>
          </div>
        </div>
      </Card>

      {/* Menu buttons */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <MenuButton icon="💳" title="Пополнить баланс" subtitle="Мин. 500 ₽" href="/topup" />
        <MenuButton icon="🧾" title="История транзакций" subtitle="Пополнения и платежи" href="/billing/history" />
        <MenuButton icon="👥" title="Реферальная программа" subtitle="Приглашайте друзей" href="/referral" />
        <MenuButton
          icon={plan?.emoji ?? '⭐'}
          title={`Тариф: ${plan?.displayName ?? '—'}`}
          subtitle={plan ? `${plan.displayName} · активен` : ''}
          href="/plans"
        />
        <MenuButton icon="📋" title="Юридический профиль" subtitle="Реквизиты, статус, документы" href="/legal-profile/view" />
        <MenuButton icon="📄" title="Мои договоры" subtitle="Просмотр и подписание" href="/contracts" />
      </div>

      {/* Reputation */}
      <Card title="Репутация">
        {statsLoading ? (
          <Skeleton className="h-20" />
        ) : (
          <div className="space-y-4">
            {/* Advertiser reputation */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm text-text-secondary">Рекламодатель</span>
                <span className="text-sm font-semibold text-text-primary">
                  {advertiserScore.toFixed(1)} / 5.0
                </span>
              </div>
              <div className="w-full h-2.5 bg-harbor-elevated rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-normal ${getScoreColor(advertiserScore)}`}
                  style={{ width: `${(advertiserScore / 5) * 100}%` }}
                />
              </div>
            </div>
            {/* Owner reputation */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm text-text-secondary">Владелец канала</span>
                <span className="text-sm font-semibold text-text-primary">
                  {ownerScore.toFixed(1)} / 5.0
                </span>
              </div>
              <div className="w-full h-2.5 bg-harbor-elevated rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-normal ${getScoreColor(ownerScore)}`}
                  style={{ width: `${(ownerScore / 5) * 100}%` }}
                />
              </div>
            </div>
            <div className="pt-2 text-right">
              <a
                href="/profile/reputation"
                className="text-xs text-accent hover:underline"
              >
                История изменений →
              </a>
            </div>
          </div>
        )}
      </Card>

      {/* Tax reminder */}
      {user && parseFloat(user.earned_rub) > 0 && (
        <Notification type="warning">
          <span className="text-sm">
            💡 Налоговая информация: Ваш заработок: {formatCurrency(user.earned_rub)}. Не забудьте задекларировать доход.
          </span>
        </Notification>
      )}
    </div>
  )
}
