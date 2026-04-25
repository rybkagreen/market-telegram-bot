import { useNavigate } from 'react-router-dom'
import { ScreenLayout } from '@/components/layout/ScreenLayout'
import { Card, MenuButton, StatGrid, ReputationBar, Notification, Skeleton } from '@/components/ui'
import { Text } from '@/components/ui/Text'
import { PLAN_INFO } from '@/lib/constants'
import { formatCurrency } from '@/lib/formatters'
import { useMe, useMyStats } from '@/hooks/queries'
import { useOpenInWebPortal } from '@/hooks/useOpenInWebPortal'
import styles from './Cabinet.module.css'

export default function Cabinet() {
  const navigate = useNavigate()
  const { data: user, isLoading: userLoading, isError: userError } = useMe()
  const { data: stats, isLoading: statsLoading } = useMyStats()

  // Phase 1 §1.B.2: legal-profile and contracts UI moved to web_portal
  // (ФЗ-152). The mini_app surfaces a "Open in portal" entry per flow;
  // the underlying click mints a ticket via useOpenInWebPortal.
  const openLegalProfile = useOpenInWebPortal('/legal-profile/view')
  const openContracts = useOpenInWebPortal('/contracts')

  const plan = user ? PLAN_INFO[user.plan] : null
  const earnedAmount = user ? parseFloat(user.earned_rub) : 0

  return (
    <ScreenLayout title="Кабинет">
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
              ]}
            />
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
        subtitle="Откроется в веб-портале"
        onClick={() => openLegalProfile.mutate()}
      />

      <MenuButton
        icon="📄"
        title="Мои договоры"
        subtitle="Откроется в веб-портале"
        onClick={() => openContracts.mutate()}
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
          <Text variant="sm">
            💡 Налоговая информация: Ваш заработок:{' '}
            {user && formatCurrency(user.earned_rub)}. Не забудьте задекларировать доход.
          </Text>
        </Notification>
      )}
    </ScreenLayout>
  )
}
