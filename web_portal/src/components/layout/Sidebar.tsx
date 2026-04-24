import { useLocation, useNavigate } from 'react-router-dom'
import { Icon, type IconName } from '@shared/ui'
import { usePortalUiStore } from '@/stores/portalUiStore'
import { useAuthStore } from '@/stores/authStore'
import { useMe } from '@/hooks/queries'
import { useMyChannels } from '@/hooks/useChannelQueries'
import { useMyPlacements } from '@/hooks/useCampaignQueries'

interface NavItem {
  id: string
  label: string
  path: string
  icon: IconName
  badge?: string
  count?: number
  adminOnly?: boolean
}

interface NavSection {
  group: string | null
  items: NavItem[]
}

export function Sidebar() {
  const location = useLocation()
  const navigate = useNavigate()
  const { sidebarMode } = usePortalUiStore()
  const { user } = useAuthStore()
  const { data: me } = useMe()
  const { data: ownedChannels } = useMyChannels()
  const { data: activeCampaigns } = useMyPlacements('advertiser', 'active')

  const isCollapsed = sidebarMode === 'collapsed'
  const campaignsCount = Array.isArray(activeCampaigns) ? activeCampaigns.length : 0
  const channelsCount = ownedChannels?.length ?? 0
  const planLabel = me?.plan && me.plan !== 'free' ? me.plan.toUpperCase() : null

  const sections: NavSection[] = [
    {
      group: 'Финансы',
      items: [
        { id: 'plans', label: 'Тариф', path: '/plans', icon: 'tariff', badge: planLabel ?? undefined },
        { id: 'topup', label: 'Пополнить', path: '/topup', icon: 'topup' },
        { id: 'billing', label: 'Транзакции', path: '/billing/history', icon: 'receipt' },
        { id: 'payouts', label: 'Выплаты', path: '/own/payouts', icon: 'payouts' },
      ],
    },
    {
      group: 'Реклама',
      items: [
        {
          id: 'campaigns',
          label: 'Кампании',
          path: '/adv/campaigns',
          icon: 'campaign',
          count: campaignsCount || undefined,
        },
      ],
    },
    {
      group: 'Каналы',
      items: [
        {
          id: 'channels',
          label: 'Каналы',
          path: '/own/channels',
          icon: 'channels',
          count: channelsCount || undefined,
        },
        { id: 'own-requests', label: 'Размещения', path: '/own/requests', icon: 'placement' },
      ],
    },
    {
      group: 'Аналитика',
      items: [
        { id: 'analytics', label: 'Аналитика', path: '/analytics', icon: 'analytics' },
      ],
    },
    {
      group: 'Юридический',
      items: [
        { id: 'acts', label: 'Акты', path: '/acts', icon: 'docs' },
        { id: 'contracts', label: 'Договоры', path: '/contracts', icon: 'contract' },
        { id: 'legal', label: 'Профиль', path: '/legal-profile/view', icon: 'verified' },
      ],
    },
    {
      group: 'Прочее',
      items: [
        { id: 'referral', label: 'Реферальная', path: '/referral', icon: 'referral' },
        { id: 'help', label: 'Помощь', path: '/help', icon: 'info' },
        { id: 'feedback', label: 'Обратная связь', path: '/feedback', icon: 'feedback' },
      ],
    },
  ]

  if (user?.is_admin) {
    sections.push({
      group: 'Администрирование',
      items: [
        { id: 'admin', label: 'Админ-панель', path: '/admin', icon: 'admin', adminOnly: true },
        { id: 'admin-users', label: 'Пользователи', path: '/admin/users', icon: 'users', adminOnly: true },
        { id: 'admin-disputes', label: 'Споры', path: '/admin/disputes', icon: 'disputes', adminOnly: true },
        { id: 'admin-feedback', label: 'Обращения', path: '/admin/feedback', icon: 'requests', adminOnly: true },
        { id: 'admin-payouts', label: 'Выплаты', path: '/admin/payouts', icon: 'payouts', adminOnly: true },
        { id: 'admin-acc', label: 'Бухгалтерия', path: '/admin/accounting', icon: 'accounting', adminOnly: true },
        { id: 'admin-tax', label: 'Налоги', path: '/admin/tax-summary', icon: 'taxes', adminOnly: true },
        { id: 'admin-settings', label: 'Реквизиты платформы', path: '/admin/settings', icon: 'settings', adminOnly: true },
      ],
    })
  }

  sections.push({
    group: null,
    items: [{ id: 'cabinet', label: 'Кабинет', path: '/cabinet', icon: 'cabinet' }],
  })

  const isItemActive = (path: string) =>
    location.pathname === path ||
    (path !== '/cabinet' && location.pathname.startsWith(path + '/'))

  const handleNavigate = (path: string) => navigate(path)

  return (
    <aside
      className={`h-dvh min-h-0 flex flex-col bg-harbor-secondary border-r border-border transition-[width] duration-300 flex-shrink-0 ${
        isCollapsed ? 'w-16' : 'w-60'
      }`}
      aria-label="Основная навигация"
    >
      {/* Logo */}
      <div className={`flex items-center pt-4 pb-3 ${isCollapsed ? 'justify-center px-2' : 'px-4'}`}>
        {isCollapsed ? (
          <picture key="logo-icon">
            <source srcSet="/brand/rekharbor_icon_dark.svg" media="(prefers-color-scheme: light)" />
            <img
              src="/brand/rekharbor_icon_teal.svg"
              alt="RekHarbor"
              width={32}
              height={32}
              className="block shrink-0"
            />
          </picture>
        ) : (
          <picture key="logo-full">
            <source srcSet="/brand/rekharbor_full_light.svg" media="(prefers-color-scheme: light)" />
            <img
              src="/brand/rekharbor_full_dark.svg"
              alt="RekHarbor"
              width={158}
              height={32}
              className="block shrink-0 h-8 w-[158px]"
            />
          </picture>
        )}
      </div>

      {/* Waterline */}
      <div
        className="h-px mx-3.5 mb-2"
        style={{
          background:
            'linear-gradient(90deg, transparent, var(--color-border) 30%, var(--color-border) 70%, transparent)',
        }}
      />

      {/* Nav */}
      <nav className={`flex-1 overflow-y-auto scrollbar-thin pb-3.5 ${isCollapsed ? 'px-2' : 'px-2'}`}>
        {sections.map((section, idx) => (
          <div key={idx} className="mb-2.5">
            {section.group && !isCollapsed && (
              <div className="text-[10px] font-semibold uppercase tracking-[0.09em] text-text-tertiary px-2 pt-2 pb-1">
                {section.group}
              </div>
            )}
            {section.items.map((item) => {
              const active = isItemActive(item.path)
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => handleNavigate(item.path)}
                  title={isCollapsed ? item.label : undefined}
                  className={`group relative w-full flex items-center gap-2.5 rounded-md text-left transition-colors text-[13.5px] font-medium ${
                    isCollapsed ? 'justify-center px-2 py-2.5' : 'px-2 py-2'
                  } ${
                    active
                      ? 'bg-accent-muted text-accent font-semibold'
                      : 'text-text-secondary hover:bg-harbor-card hover:text-text-primary'
                  } cursor-pointer`}
                >
                  {active && (
                    <span
                      aria-hidden="true"
                      className="absolute left-[-8px] top-2 bottom-2 w-0.5 bg-accent rounded-r"
                    />
                  )}
                  <Icon name={item.icon} size={17} variant={active ? 'fill' : 'outline'} />
                  {!isCollapsed && <span className="flex-1 whitespace-nowrap">{item.label}</span>}
                  {!isCollapsed && item.badge && (
                    <span className="text-[9.5px] font-semibold tracking-[0.05em] uppercase px-1.5 py-0.5 rounded bg-accent-2-muted text-accent-2">
                      {item.badge}
                    </span>
                  )}
                  {!isCollapsed && item.count != null && (
                    <span
                      className={`text-[11px] font-semibold font-mono min-w-[20px] text-center rounded-full px-1.5 py-0.5 ${
                        active
                          ? 'bg-accent text-white'
                          : 'bg-harbor-elevated text-text-secondary'
                      }`}
                    >
                      {item.count}
                    </span>
                  )}
                </button>
              )
            })}
          </div>
        ))}
      </nav>
    </aside>
  )
}
