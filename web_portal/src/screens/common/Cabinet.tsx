import { useState } from 'react'
import { Card, Notification, Skeleton, MenuButton, Button } from '@shared/ui'
import { formatCurrency, PLAN_INFO } from '@/lib/constants'
import { useMe, useMyStats } from '@/hooks/queries'
import { api } from '@shared/api/client'

export default function Cabinet() {
  const { data: user, isLoading: userLoading, isError: userError } = useMe()
  const { data: stats, isLoading: statsLoading } = useMyStats()

  const [convertAmount, setConvertAmount] = useState('')
  const [showConvert, setShowConvert] = useState(false)
  const [converting, setConverting] = useState(false)
  const [convertError, setConvertError] = useState<string | null>(null)
  const [convertSuccess, setConvertSuccess] = useState(false)

  const handleConvert = () => {
    const amt = parseInt(convertAmount, 10)
    if (!amt || amt <= 0) return
    setConverting(true)
    setConvertError(null)
    setConvertSuccess(false)
    api.post('billing/convert-credits', { json: { amount_rub: amt } })
      .json()
      .then(() => {
        setConvertSuccess(true)
        setConvertAmount('')
        setTimeout(() => setShowConvert(false), 2000)
      })
      .catch(() => setConvertError('Ошибка при конвертации'))
      .finally(() => setConverting(false))
  }

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
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
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
          <div className="text-center p-4 bg-harbor-elevated rounded-lg">
            <p className="text-2xl font-bold text-purple-400">
              {user ? user.credits : '—'}
            </p>
            <p className="text-sm text-text-secondary mt-1">🎟 Кредиты</p>
          </div>
        </div>

        {/* Credits converter */}
        <div className="mt-4 pt-4 border-t border-border">
          {!showConvert ? (
            <Button variant="ghost" size="sm" onClick={() => setShowConvert(true)}>
              💱 Конвертировать ₽ → кредиты
            </Button>
          ) : (
            <div className="flex gap-2 items-end flex-wrap">
              <div>
                <label className="block text-xs text-text-secondary mb-1">Сумма в ₽</label>
                <input
                  className="w-32 px-3 py-2 bg-harbor-elevated border border-border rounded-md text-sm text-text-primary focus:border-accent focus:outline-none"
                  type="number"
                  min="1"
                  placeholder="Сумма"
                  value={convertAmount}
                  onChange={(e) => setConvertAmount(e.target.value)}
                />
              </div>
              <Button size="sm" loading={converting} disabled={!convertAmount} onClick={handleConvert}>
                Обменять
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setShowConvert(false)}>Отмена</Button>
            </div>
          )}
          {convertError && <Notification type="danger" className="mt-2">{convertError}</Notification>}
          {convertSuccess && <Notification type="success" className="mt-2">Кредиты зачислены</Notification>}
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
                  className={`h-full rounded-full transition-all duration-normal ${
                    advertiserScore >= 4 ? 'bg-success' : advertiserScore >= 3 ? 'bg-warning' : 'bg-danger'
                  }`}
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
                  className={`h-full rounded-full transition-all duration-normal ${
                    ownerScore >= 4 ? 'bg-success' : ownerScore >= 3 ? 'bg-warning' : 'bg-danger'
                  }`}
                  style={{ width: `${(ownerScore / 5) * 100}%` }}
                />
              </div>
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
