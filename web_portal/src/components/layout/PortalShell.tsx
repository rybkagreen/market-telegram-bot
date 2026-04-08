import { useEffect } from 'react'
import type { ReactNode } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useMediaQuery, breakpoints } from '@shared/hooks/useMediaQuery'
import { useAuthStore } from '@/stores/authStore'
import { usePortalUiStore } from '@/stores/portalUiStore'
import {
  LayoutDashboard,
  Users,
  Megaphone,
  BarChart3,
  Settings,
  LogOut,
  Menu,
  X,
  ChevronRight,
  Bell,
  Wallet,
  FileText,
  MessageSquare,
  CreditCard,
  PlusCircle,
  Banknote,
  ScrollText,
  UserCheck,
  Scale,
} from 'lucide-react'

interface NavItem {
  icon: ReactNode
  label: string
  path: string
  adminOnly?: boolean
}

const navItems: NavItem[] = [
  { icon: <LayoutDashboard size={20} />, label: 'Дашборд', path: '/' },
  { icon: <Wallet size={20} />, label: 'Кабинет', path: '/cabinet' },
  { icon: <CreditCard size={20} />, label: 'Тариф', path: '/plans' },
  { icon: <PlusCircle size={20} />, label: 'Пополнить', path: '/topup' },
  { icon: <Megaphone size={20} />, label: 'Кампании', path: '/adv/campaigns' },
  { icon: <BarChart3 size={20} />, label: 'Аналитика', path: '/adv/analytics' },
  { icon: <FileText size={20} />, label: 'Размещения', path: '/own/requests' },
  { icon: <Users size={20} />, label: 'Каналы', path: '/own/channels' },
  { icon: <Banknote size={20} />, label: 'Выплаты', path: '/own/payouts' },
  { icon: <ScrollText size={20} />, label: 'Документы', path: '/contracts' },
  { icon: <UserCheck size={20} />, label: 'Реферальная', path: '/referral' },
  { icon: <MessageSquare size={20} />, label: 'Обратная связь', path: '/feedback' },
  { icon: <Settings size={20} />, label: 'Настройки', path: '/settings' },
]

const adminItems: NavItem[] = [
  { icon: <LayoutDashboard size={20} />, label: 'Админ-панель', path: '/admin', adminOnly: true },
  { icon: <Users size={20} />, label: 'Пользователи', path: '/admin/users', adminOnly: true },
  { icon: <Scale size={20} />, label: 'Споры', path: '/admin/disputes', adminOnly: true },
  { icon: <Bell size={20} />, label: 'Обращения', path: '/admin/feedback', adminOnly: true },
  { icon: <BarChart3 size={20} />, label: 'Бухгалтерия', path: '/admin/accounting', adminOnly: true },
  { icon: <LayoutDashboard size={20} />, label: 'Налоги', path: '/admin/tax-summary', adminOnly: true },
  { icon: <Settings size={20} />, label: 'Настройки платформы', path: '/admin/settings', adminOnly: true },
]

// Breadcrumb mapping
const breadcrumbMap: Record<string, string[]> = {
  '/': ['Главная'],
  '/cabinet': ['Кабинет'],
  '/plans': ['Тариф'],
  '/topup': ['Пополнить баланс'],
  '/referral': ['Реферальная программа'],
  '/contracts': ['Документы'],
  '/acts': ['Мои акты'],
  '/adv/campaigns': ['Кампании', 'Мои кампании'],
  '/adv/analytics': ['Аналитика'],
  '/own/requests': ['Размещения'],
  '/own/channels': ['Каналы'],
  '/own/payouts': ['Выплаты'],
  '/feedback': ['Обратная связь'],
  '/admin': ['Админ-панель'],
  '/admin/users': ['Админ-панель', 'Пользователи'],
  '/admin/disputes': ['Админ-панель', 'Споры'],
  '/admin/feedback': ['Админ-панель', 'Обращения'],
  '/admin/accounting': ['Админ-панель', 'Бухгалтерия'],
  '/admin/tax-summary': ['Админ-панель', 'Налоги'],
  '/admin/settings': ['Админ-панель', 'Настройки платформы'],
}

export function PortalShell() {
  const { sidebarOpen, toggleSidebar, setSidebarOpen } = usePortalUiStore()
  const isDesktop = useMediaQuery(breakpoints.md)
  const location = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()

  // Sidebar открыт: на десктопе — по умолчанию открыт, на мобильном — по toggle
  const showSidebar = sidebarOpen

  // На мобильном — закрыть sidebar при монтировании и при ресайзе
  useEffect(() => {
    if (!isDesktop) {
      setSidebarOpen(false)
    }
  }, [isDesktop, setSidebarOpen])

  const breadcrumbs = breadcrumbMap[location.pathname] || ['Главная']

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="flex h-dvh overflow-hidden bg-harbor-bg">
      {/* Mobile overlay */}
      {!isDesktop && showSidebar && (
        <div
          className="fixed inset-0 bg-black/50 z-40"
          onClick={() => setSidebarOpen(false)}
          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setSidebarOpen(false) }}
          tabIndex={0}
          role="button"
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed md:relative z-50 md:z-0
          h-full bg-harbor-card border-r border-border
          transition-all duration-300
          ${showSidebar
            ? 'w-60 translate-x-0 overflow-visible md:w-60 md:translate-x-0'
            : 'w-0 -translate-x-full overflow-hidden pointer-events-none md:w-0 md:translate-x-0 md:overflow-hidden md:pointer-events-none'}
        `}
      >
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="px-5 py-4 border-b border-border flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-2xl">⚓</span>
              <span className="font-display font-bold text-lg text-text-primary">RekHarbor</span>
            </div>
            {!isDesktop && showSidebar && (
              <button onClick={() => setSidebarOpen(false)} className="text-text-secondary hover:text-text-primary">
                <X size={20} />
              </button>
            )}
          </div>

          {/* Nav items */}
          <nav className="flex-1 overflow-y-auto py-4 scrollbar-thin">
            {navItems.map((item) => (
              <button
                key={item.path}
                onClick={() => { navigate(item.path); if (!isDesktop) setSidebarOpen(false) }}
                className={`
                  w-full flex items-center gap-3 px-5 py-2.5 text-sm font-medium
                  transition-colors duration-fast
                  ${location.pathname === item.path || location.pathname.startsWith(item.path + '/')
                    ? 'bg-accent-muted text-accent border-r-2 border-accent'
                    : 'text-text-secondary hover:bg-harbor-elevated hover:text-text-primary'}
                `}
              >
                {item.icon}
                <span>{item.label}</span>
              </button>
            ))}

            {user?.is_admin && (
              <>
                <div className="px-5 py-2 mt-2 text-xs font-semibold text-text-tertiary uppercase tracking-wider">
                  Администрирование
                </div>
                {adminItems.map((item) => (
                  <button
                    key={item.path}
                    onClick={() => { navigate(item.path); if (!isDesktop) setSidebarOpen(false) }}
                    className={`
                      w-full flex items-center gap-3 px-5 py-2.5 text-sm font-medium
                      transition-colors duration-fast
                      ${location.pathname === item.path || location.pathname.startsWith(item.path + '/')
                        ? 'bg-accent-muted text-accent border-r-2 border-accent'
                        : 'text-text-secondary hover:bg-harbor-elevated hover:text-text-primary'}
                    `}
                  >
                    {item.icon}
                    <span>{item.label}</span>
                  </button>
                ))}
              </>
            )}
          </nav>

          {/* User info + logout */}
          <div className="px-5 py-4 border-t border-border">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-accent-muted flex items-center justify-center text-accent font-semibold text-sm">
                {user?.first_name?.[0]?.toUpperCase() ?? 'U'}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-text-primary truncate">{user?.first_name || 'Пользователь'}</p>
                <p className="text-xs text-text-tertiary truncate">@{user?.username || 'unknown'}</p>
              </div>
              <button onClick={handleLogout} className="text-text-tertiary hover:text-danger transition-colors" title="Выйти">
                <LogOut size={16} />
              </button>
            </div>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="h-16 bg-harbor-card border-b border-border flex items-center px-4 lg:px-6 gap-4 shrink-0">
          {/* Hamburger */}
          <button
            onClick={toggleSidebar}
            className="text-text-secondary hover:text-text-primary transition-colors"
          >
            <Menu size={20} />
          </button>

          {/* Breadcrumbs */}
          <nav className="flex items-center gap-1 text-sm text-text-secondary">
            {breadcrumbs.map((crumb, i) => (
              <span key={i} className="flex items-center gap-1">
                {i > 0 && <ChevronRight size={14} className="text-text-tertiary" />}
                <span className={i === breadcrumbs.length - 1 ? 'text-text-primary font-medium' : ''}>
                  {crumb}
                </span>
              </span>
            ))}
          </nav>

          {/* Spacer */}
          <div className="flex-1" />

          {/* Plan badge */}
          {user?.plan && (
            <span className="hidden sm:inline-flex px-2.5 py-1 rounded-full text-xs font-medium bg-accent-muted text-accent">
              {user.plan.charAt(0).toUpperCase() + user.plan.slice(1)}
            </span>
          )}
        </header>

        {/* Scrollable content */}
        <main className="flex-1 overflow-y-auto scrollbar-thin bg-harbor-bg">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
