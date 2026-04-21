import { useNavigate } from 'react-router-dom'
import { Button, Notification, Skeleton, Icon } from '@shared/ui'
import { useMe } from '@/hooks/queries'
import { BalanceHero } from './cabinet/BalanceHero'
import { PerformanceChart } from './cabinet/PerformanceChart'
import { QuickActions } from './cabinet/QuickActions'
import { NotificationsCard } from './cabinet/NotificationsCard'
import { ProfileCompleteness } from './cabinet/ProfileCompleteness'
import { RecommendedChannels } from './cabinet/RecommendedChannels'
import { RecentActivity } from './cabinet/RecentActivity'

export default function Cabinet() {
  const { data: user, isLoading, isError } = useMe()
  const navigate = useNavigate()

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-20" />
        <Skeleton className="h-40" />
      </div>
    )
  }

  if (isError || !user) {
    return <Notification type="danger">Не удалось загрузить данные</Notification>
  }

  const greetingName = user.first_name?.trim() || 'пользователь'

  return (
    <div className="space-y-6">
      {/* Greeting */}
      <header className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.09em] text-text-tertiary">
            <Icon name="wave" size={12} />
            {user.is_admin ? 'Админ-панель' : 'Кабинет рекламодателя'}
          </div>
          <h1 className="mt-2 font-display text-[26px] leading-tight tracking-[-0.02em] font-bold text-text-primary">
            С возвращением, {greetingName}
          </h1>
          <p className="text-sm text-text-secondary mt-1">
            Здесь собрана сводка по балансу, активным кампаниям и событиям, которые требуют внимания.
          </p>
        </div>
        <div className="flex gap-2 flex-shrink-0">
          <Button variant="secondary" size="sm" iconLeft="analytics" onClick={() => navigate('/adv/analytics')}>
            Отчёт
          </Button>
          <Button variant="primary" size="sm" iconLeft="plus" onClick={() => navigate('/adv/campaigns/new/category')}>
            Создать кампанию
          </Button>
        </div>
      </header>

      {/* Balance hero */}
      <BalanceHero />

      {/* Main grid: chart + sidebar widgets */}
      <div className="grid grid-cols-1 xl:grid-cols-[1.6fr_1fr] gap-4">
        <div className="space-y-4">
          <PerformanceChart />
          <QuickActions role="advertiser" />
        </div>
        <div className="space-y-4">
          <NotificationsCard />
          <ProfileCompleteness />
        </div>
      </div>

      {/* Recommended channels */}
      <RecommendedChannels />

      {/* Recent activity */}
      <RecentActivity />

      {/* Footer waterline */}
      <footer className="mt-2 flex items-center justify-center gap-2 text-[11px] text-text-tertiary font-mono">
        <Icon name="compass" size={12} />
        RekHarbor v2 · обновлено {new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}
      </footer>
    </div>
  )
}
