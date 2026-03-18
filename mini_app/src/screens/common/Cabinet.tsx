import { useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Card, MenuButton, StatGrid, ReputationBar, Notification, Skeleton } from '@/components/ui'
import { PLAN_INFO } from '@/lib/constants'
import { formatCurrency } from '@/lib/formatters'
import { useMe, useMyStats } from '@/hooks/queries'
import styles from './Cabinet.module.css'

export default function Cabinet() {
  const navigate = useNavigate()
  const { data: user, isLoading: userLoading, isError: userError } = useMe()
  const { data: stats, isLoading: statsLoading } = useMyStats()
  const plan = user ? PLAN_INFO[user.plan] : null
  const earnedAmount = user ? parseFloat(user.earned_rub) : 0

  return (
    <ScreenShell>
      <Card title="Ваши балансы">
        {userLoading ? (
          <Skeleton height={60} />
        ) : userError ? (
          <Notification type="danger">Не удалось загрузить данные</Notification>
        ) : (
          <StatGrid
            items={[
              { value: formatCurrency(user!.balance_rub), label: '💳 Баланс рекл.', color: 'blue' },
              { value: formatCurrency(user!.earned_rub), label: '💰 Заработок', color: 'green' },
            ]}
          />
        )}
      </Card>

      <MenuButton
        icon="💳"
        title="Пополнить баланс"
        subtitle="Мин. 500 ₽"
        onClick={() => navigate('/topup')}
      />

      <MenuButton
        icon="⭐"
        iconBg="var(--rh-warning-muted)"
        title={plan ? `Тариф: ${plan.displayName}` : 'Тариф: —'}
        subtitle={plan ? `${plan.price > 0 ? plan.price + ' ₽/мес' : 'Бесплатно'} · активен` : ''}
        onClick={() => navigate('/plans')}
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
