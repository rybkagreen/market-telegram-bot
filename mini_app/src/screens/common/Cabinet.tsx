import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Card, MenuButton, StatGrid, ReputationBar, Notification, Skeleton, Button } from '@/components/ui'
import { PLAN_INFO } from '@/lib/constants'
import { formatCurrency } from '@/lib/formatters'
import { useMe, useMyStats } from '@/hooks/queries'
import { useContracts } from '@/hooks/useContractQueries'
import { useMyLegalProfile } from '@/hooks/useLegalProfileQueries'
import { useBuyCredits } from '@/hooks/queries/useBillingQueries'
import styles from './Cabinet.module.css'

const KEP_NEEDS_STATUSES = ['legal_entity', 'individual_entrepreneur']

export default function Cabinet() {
  const navigate = useNavigate()
  const { data: user, isLoading: userLoading, isError: userError } = useMe()
  const { data: stats, isLoading: statsLoading } = useMyStats()
  const { data: profile } = useMyLegalProfile()
  const { data: contractsList } = useContracts()
  const buyCredits = useBuyCredits()
  const [convertAmount, setConvertAmount] = useState('')
  const [showConvert, setShowConvert] = useState(false)
  const plan = user ? PLAN_INFO[user.plan] : null
  const earnedAmount = user ? parseFloat(user.earned_rub) : 0

  const legalStatus = profile?.legal_status ?? ''
  const hasPendingKepNeeds =
    KEP_NEEDS_STATUSES.includes(legalStatus) &&
    (contractsList?.items.some((c) => c.contract_status === 'signed' && !c.kep_requested) ?? false)

  return (
    <ScreenShell>
      <Card title="Ваши балансы">
        {userLoading ? (
          <Skeleton height={60} />
        ) : userError ? (
          <Notification type="danger">Не удалось загрузить данные</Notification>
        ) : (
          <>
            <StatGrid
              items={[
                { value: formatCurrency(user!.balance_rub), label: '💳 Баланс рекл.', color: 'blue' },
                { value: formatCurrency(user!.earned_rub), label: '💰 Заработок', color: 'green' },
                { value: String(user!.credits), label: '🎟 Кредиты', color: 'purple' },
              ]}
            />
            {!showConvert ? (
              <div style={{ marginTop: 'var(--rh-space-3)' }}>
                <Button size="sm" variant="secondary" onClick={() => setShowConvert(true)}>
                  Конвертировать ₽ → кредиты
                </Button>
              </div>
            ) : (
              <div style={{ marginTop: 'var(--rh-space-3)', display: 'flex', gap: 'var(--rh-space-2)', alignItems: 'center', flexWrap: 'wrap' }}>
                <input
                  type="number"
                  min="1"
                  placeholder="Сумма в ₽"
                  value={convertAmount}
                  onChange={(e) => setConvertAmount(e.target.value)}
                  style={{ padding: 'var(--rh-space-2) var(--rh-space-3)', borderRadius: 'var(--rh-radius-md)', border: '1px solid var(--rh-border-color)', background: 'var(--rh-bg-elevated)', color: 'var(--rh-text-primary)', width: '140px' }}
                />
                <Button
                  size="sm"
                  disabled={buyCredits.isPending || !convertAmount}
                  onClick={() => {
                    const amt = parseInt(convertAmount, 10)
                    if (amt > 0) buyCredits.mutate(amt, { onSuccess: () => { setConvertAmount(''); setShowConvert(false) } })
                  }}
                >
                  {buyCredits.isPending ? '...' : 'Обменять'}
                </Button>
                <Button size="sm" variant="secondary" onClick={() => setShowConvert(false)}>Отмена</Button>
              </div>
            )}
          </>
        )}
      </Card>

      <MenuButton
        icon="💳"
        title="Пополнить баланс"
        subtitle="Мин. 500 ₽"
        onClick={() => navigate('/topup')}
      />

      <MenuButton
        icon="🧾"
        title="История транзакций"
        subtitle="Пополнения и платежи"
        onClick={() => navigate('/billing/history')}
      />

      <MenuButton
        icon="👥"
        title="Реферальная программа"
        subtitle="Приглашайте друзей — получайте кредиты"
        onClick={() => navigate('/referral')}
      />

      <MenuButton
        icon="⭐"
        iconBg="var(--rh-warning-muted)"
        title={plan ? `Тариф: ${plan.displayName}` : 'Тариф: —'}
        subtitle={
          plan
            ? `${plan.price > 0 ? plan.price + ' ₽/мес' : 'Бесплатно'} · активен`
            : ''
        }
        onClick={() => navigate('/plans')}
      />

      <MenuButton
        icon="📋"
        title="Юридический профиль"
        subtitle="Реквизиты, статус, документы"
        onClick={() => navigate('/legal-profile/view')}
      />

      <MenuButton
        icon="📄"
        title="Мои договоры"
        subtitle={hasPendingKepNeeds ? '⚠️ Рекомендуется запросить КЭП' : 'Просмотр и подписание договоров'}
        onClick={() => navigate('/contracts')}
      />

      <Card title="Репутация">
        {statsLoading ? (
          <Skeleton height={80} />
        ) : stats?.reputation ? (
          <>
            <ReputationBar
              label="Рекламодатель"
              score={stats.reputation.advertiser_score ?? 5.0}
            />
            <div className={styles.reputationGap}>
              <ReputationBar
                label="Владелец канала"
                score={stats.reputation.owner_score ?? 5.0}
              />
            </div>
          </>
        ) : (
          <Notification type="info">Загрузка репутации...</Notification>
        )}
      </Card>

      {earnedAmount > 0 && (
        <Notification type="warning">
          <span style={{ fontSize: 'var(--rh-text-sm)' }}>
            💡 Налоговая информация: Ваш заработок:{' '}
            {user && formatCurrency(user.earned_rub)}. Не забудьте задекларировать доход.
          </span>
        </Notification>
      )}
    </ScreenShell>
  )
}
