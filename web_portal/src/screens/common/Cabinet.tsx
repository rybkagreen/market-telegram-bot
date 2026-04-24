import { useNavigate } from 'react-router-dom'
import { Button, Notification, Skeleton, Icon } from '@shared/ui'
import { useMe } from '@/hooks/queries'
import { useAuthStore } from '@/stores/authStore'
import { BalanceHero } from './cabinet/BalanceHero'
import { PerformanceChart } from './cabinet/PerformanceChart'
import { QuickActions } from './cabinet/QuickActions'
import { NotificationsCard } from './cabinet/NotificationsCard'
import { ProfileCompleteness } from './cabinet/ProfileCompleteness'
import { RecommendedChannels } from './cabinet/RecommendedChannels'
import { RecentActivity } from './cabinet/RecentActivity'

export default function Cabinet() {
  const { data: user, isLoading, isError } = useMe()
  const { logout } = useAuthStore()
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
  const displayHandle = user.username ? `@${user.username}` : '—'
  const initial = greetingName.slice(0, 1).toUpperCase()

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
          <Button variant="secondary" size="sm" iconLeft="analytics" onClick={() => navigate('/analytics')}>
            Аналитика
          </Button>
          <Button variant="primary" size="sm" iconLeft="plus" onClick={() => navigate('/adv/campaigns/new/category')}>
            Создать кампанию
          </Button>
        </div>
      </header>

      {/* Account card */}
      <div className="flex items-center gap-3 p-4 bg-harbor-card border border-border rounded-xl sm:gap-4">
        <div
          className="w-12 h-12 rounded-xl grid place-items-center text-white font-display font-bold text-lg flex-shrink-0"
          style={{
            background: 'linear-gradient(135deg, var(--color-accent-2), var(--color-accent))',
          }}
        >
          {initial}
        </div>

        {/* Mobile: compact name + handle + tg-id. Desktop: 3-col grid. */}
        <div className="flex-1 min-w-0 sm:grid sm:grid-cols-3 sm:gap-4">
          <div className="min-w-0 sm:block">
            <div className="hidden sm:block text-[10px] font-semibold uppercase tracking-[0.09em] text-text-tertiary">Имя</div>
            <div className="text-[15px] sm:text-[14px] font-semibold text-text-primary truncate">{greetingName}</div>
            <div className="sm:hidden text-[12px] text-text-secondary truncate">
              {displayHandle} · <span className="font-mono tabular-nums text-text-tertiary">{user.telegram_id}</span>
            </div>
          </div>
          <div className="hidden sm:block min-w-0">
            <div className="text-[10px] font-semibold uppercase tracking-[0.09em] text-text-tertiary">Username</div>
            <div className="text-[14px] text-text-secondary truncate">{displayHandle}</div>
          </div>
          <div className="hidden sm:block min-w-0">
            <div className="text-[10px] font-semibold uppercase tracking-[0.09em] text-text-tertiary">Telegram ID</div>
            <div className="text-[14px] font-mono tabular-nums text-text-secondary truncate">
              {user.telegram_id}
            </div>
          </div>
        </div>

        <Button
          variant="secondary"
          size="sm"
          icon
          onClick={logout}
          title="Выйти"
          aria-label="Выйти"
          className="sm:hidden !w-11 !h-11 flex-shrink-0"
        >
          <Icon name="logout" size={16} />
        </Button>
        <Button variant="secondary" size="sm" iconLeft="logout" onClick={logout} className="hidden sm:inline-flex">
          Выйти
        </Button>
      </div>

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
