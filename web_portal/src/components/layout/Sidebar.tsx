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
  const { user, logout } = useAuthStore()
  const { data: me } = useMe()
  const { data: ownedChannels } = useMyChannels()
  const { data: activeCampaigns } = useMyPlacements('advertiser', 'active')

  const isCollapsed = sidebarMode === 'collapsed'
  const campaignsCount = Array.isArray(activeCampaigns) ? activeCampaigns.length : 0
  const channelsCount = ownedChannels?.length ?? 0
  const displayName = me?.first_name?.trim() || user?.first_name || 'User'
  const displayHandle = me?.username ? `@${me.username}` : user?.username ?? 'unknown'
  const initial = displayName.slice(0, 1).toUpperCase()
  const planLabel = me?.plan && me.plan !== 'free' ? me.plan.toUpperCase() : null

  const sections: NavSection[] = [
    {
      group: null,
      items: [{ id: 'cabinet', label: 'Кабинет', path: '/cabinet', icon: 'cabinet' }],
    },
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
        { id: 'adv-analytics', label: 'Аналитика', path: '/adv/analytics', icon: 'analytics' },
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
        { id: 'own-analytics', label: 'Аналитика', path: '/own/analytics', icon: 'analytics' },
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
      <div className={`flex items-center gap-2.5 pt-4 pb-3 ${isCollapsed ? 'justify-center px-2' : 'px-4'}`}>
        <div
          className="w-[30px] h-[30px] rounded-lg grid place-items-center text-white flex-shrink-0"
          style={{
            background: 'linear-gradient(135deg, var(--color-accent), var(--color-accent-2))',
            boxShadow: 'var(--shadow-harbor-glow)',
          }}
        >
          <Icon name="anchor" size={16} strokeWidth={1.75} />
        </div>
        {!isCollapsed && (
          <div className="font-display font-bold text-[17px] tracking-[-0.01em] text-text-primary">
            RekHarbor
          </div>
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
      <nav className="flex-1 overflow-y-auto scrollbar-thin px-2.5 pb-3.5">
        {sections.map((section, idx) => (
          <div key={idx} className="mb-2.5">
            {section.group && !isCollapsed && (
              <div className="text-[10px] font-semibold uppercase tracking-[0.09em] text-text-tertiary px-2.5 pt-2 pb-1">
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
                    isCollapsed ? 'justify-center px-2 py-2.5' : 'px-2.5 py-2'
                  } ${
                    active
                      ? 'bg-accent-muted text-accent font-semibold'
                      : 'text-text-secondary hover:bg-harbor-card hover:text-text-primary'
                  } cursor-pointer`}
                >
                  {active && (
                    <span
                      aria-hidden="true"
                      className="absolute left-[-10px] top-2 bottom-2 w-0.5 bg-accent rounded-r"
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

      {/* User footer */}
      <div className={`flex items-center gap-2.5 p-3 border-t border-border ${isCollapsed ? 'justify-center' : ''}`}>
        <div
          className="w-8 h-8 rounded-lg grid place-items-center text-white font-display font-bold text-sm flex-shrink-0"
          style={{
            background: 'linear-gradient(135deg, var(--color-accent-2), var(--color-accent))',
          }}
          title={isCollapsed ? `${displayName} (${displayHandle})` : undefined}
        >
          {initial}
        </div>
        {!isCollapsed && (
          <div className="flex-1 min-w-0">
            <div className="text-[13px] font-semibold text-text-primary truncate">{displayName}</div>
            <div className="text-[11px] text-text-tertiary truncate">{displayHandle}</div>
          </div>
        )}
        <button
          type="button"
          onClick={logout}
          className="p-1 rounded text-text-tertiary hover:text-danger transition-colors cursor-pointer"
          title="Выйти"
          aria-label="Выйти"
        >
          <Icon name="logout" size={16} />
        </button>
      </div>
    </aside>
  )
}
