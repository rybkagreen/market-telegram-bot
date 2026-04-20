import { useNavigate, useLocation, Link } from 'react-router-dom'
import { Icon } from '@shared/ui'
import { usePortalUiStore } from '@/stores/portalUiStore'
import { useMediaQuery, breakpoints } from '@shared/hooks/useMediaQuery'
import { useAttentionFeed } from '@/hooks/useUserQueries'

interface Crumb {
  label: string
  path?: string
}

const BREADCRUMB_MAP: Record<string, Crumb[]> = {
  '/': [{ label: 'Главная' }],
  '/cabinet': [{ label: 'Кабинет' }],
  '/plans': [{ label: 'Тариф' }],
  '/topup': [{ label: 'Пополнить баланс' }],
  '/topup/confirm': [
    { label: 'Пополнить баланс', path: '/topup' },
    { label: 'Подтверждение' },
  ],
  '/referral': [{ label: 'Реферальная программа' }],
  '/help': [{ label: 'Центр помощи' }],
  '/feedback': [{ label: 'Обратная связь' }],
  '/billing/history': [{ label: 'Финансы' }, { label: 'История транзакций' }],
  '/profile/reputation': [{ label: 'Профиль' }, { label: 'Репутация' }],
  '/acts': [{ label: 'Мои акты' }],
  '/contracts': [
    { label: 'Документы', path: '/contracts' },
    { label: 'Договоры' },
  ],
  '/contracts/:id': [
    { label: 'Документы', path: '/contracts' },
    { label: 'Договор' },
  ],
  '/contracts/framework': [
    { label: 'Документы', path: '/contracts' },
    { label: 'Рамочный договор' },
  ],
  '/legal-profile/view': [{ label: 'Юридический профиль' }],
  '/legal-profile/documents': [
    { label: 'Юридический профиль', path: '/legal-profile/view' },
    { label: 'Документы' },
  ],
  '/legal-profile': [{ label: 'Юридический профиль' }],
  '/accept-rules': [{ label: 'Принять правила' }],

  // ── Advertiser ──
  '/adv/campaigns': [
    { label: 'Реклама', path: '/adv/campaigns' },
    { label: 'Мои кампании' },
  ],
  '/adv/campaigns/new/category': [
    { label: 'Реклама', path: '/adv/campaigns' },
    { label: 'Новая кампания' },
    { label: 'Категория' },
  ],
  '/adv/campaigns/new/channels': [
    { label: 'Реклама', path: '/adv/campaigns' },
    { label: 'Новая кампания' },
    { label: 'Каналы' },
  ],
  '/adv/campaigns/new/format': [
    { label: 'Реклама', path: '/adv/campaigns' },
    { label: 'Новая кампания' },
    { label: 'Формат' },
  ],
  '/adv/campaigns/new/text': [
    { label: 'Реклама', path: '/adv/campaigns' },
    { label: 'Новая кампания' },
    { label: 'Текст' },
  ],
  '/adv/campaigns/new/terms': [
    { label: 'Реклама', path: '/adv/campaigns' },
    { label: 'Новая кампания' },
    { label: 'Условия' },
  ],
  '/adv/campaigns/:id/waiting': [
    { label: 'Реклама', path: '/adv/campaigns' },
    { label: 'Кампания' },
    { label: 'Ожидание' },
  ],
  '/adv/campaigns/:id/payment': [
    { label: 'Реклама', path: '/adv/campaigns' },
    { label: 'Кампания' },
    { label: 'Оплата' },
  ],
  '/adv/campaigns/:id/counter-offer': [
    { label: 'Реклама', path: '/adv/campaigns' },
    { label: 'Кампания' },
    { label: 'Встречное предложение' },
  ],
  '/adv/campaigns/:id/published': [
    { label: 'Реклама', path: '/adv/campaigns' },
    { label: 'Кампания' },
    { label: 'Опубликовано' },
  ],
  '/adv/campaigns/:id/dispute': [
    { label: 'Реклама', path: '/adv/campaigns' },
    { label: 'Кампания' },
    { label: 'Спор' },
  ],
  '/adv/analytics': [
    { label: 'Реклама', path: '/adv/campaigns' },
    { label: 'Аналитика' },
  ],
  '/adv/disputes': [
    { label: 'Реклама', path: '/adv/campaigns' },
    { label: 'Споры' },
  ],
  '/campaign/:id/ord': [
    { label: 'Реклама', path: '/adv/campaigns' },
    { label: 'Кампания' },
    { label: 'ОРД' },
  ],
  '/campaign/video': [
    { label: 'Реклама', path: '/adv/campaigns' },
    { label: 'Видео-креатив' },
  ],

  // ── Owner ──
  '/own/channels': [
    { label: 'Каналы', path: '/own/channels' },
    { label: 'Мои каналы' },
  ],
  '/own/channels/add': [
    { label: 'Каналы', path: '/own/channels' },
    { label: 'Добавить канал' },
  ],
  '/own/channels/:id': [
    { label: 'Каналы', path: '/own/channels' },
    { label: 'Канал' },
  ],
  '/own/channels/:id/settings': [
    { label: 'Каналы', path: '/own/channels' },
    { label: 'Канал' },
    { label: 'Настройки' },
  ],
  '/own/requests': [
    { label: 'Каналы', path: '/own/channels' },
    { label: 'Размещения' },
  ],
  '/own/requests/:id': [
    { label: 'Каналы', path: '/own/channels' },
    { label: 'Размещения', path: '/own/requests' },
    { label: 'Детали' },
  ],
  '/own/payouts': [
    { label: 'Каналы', path: '/own/channels' },
    { label: 'Выплаты' },
  ],
  '/own/payouts/request': [
    { label: 'Каналы', path: '/own/channels' },
    { label: 'Выплаты', path: '/own/payouts' },
    { label: 'Запрос выплаты' },
  ],
  '/own/disputes': [
    { label: 'Каналы', path: '/own/channels' },
    { label: 'Споры' },
  ],
  '/own/disputes/:id': [
    { label: 'Каналы', path: '/own/channels' },
    { label: 'Споры', path: '/own/disputes' },
    { label: 'Детали' },
  ],
  '/own/analytics': [
    { label: 'Каналы', path: '/own/channels' },
    { label: 'Аналитика' },
  ],

  // ── Shared disputes ──
  '/disputes/:id': [{ label: 'Споры' }, { label: 'Детали' }],

  // ── Admin ──
  '/admin': [{ label: 'Админ-панель' }],
  '/admin/users': [
    { label: 'Админ', path: '/admin' },
    { label: 'Пользователи' },
  ],
  '/admin/users/:id': [
    { label: 'Админ', path: '/admin' },
    { label: 'Пользователи', path: '/admin/users' },
    { label: 'Детали' },
  ],
  '/admin/disputes': [
    { label: 'Админ', path: '/admin' },
    { label: 'Споры' },
  ],
  '/admin/disputes/:id': [
    { label: 'Админ', path: '/admin' },
    { label: 'Споры', path: '/admin/disputes' },
    { label: 'Детали' },
  ],
  '/admin/feedback': [
    { label: 'Админ', path: '/admin' },
    { label: 'Обращения' },
  ],
  '/admin/feedback/:id': [
    { label: 'Админ', path: '/admin' },
    { label: 'Обращения', path: '/admin/feedback' },
    { label: 'Детали' },
  ],
  '/admin/payouts': [
    { label: 'Админ', path: '/admin' },
    { label: 'Выплаты' },
  ],
  '/admin/accounting': [
    { label: 'Админ', path: '/admin' },
    { label: 'Бухгалтерия' },
  ],
  '/admin/tax-summary': [
    { label: 'Админ', path: '/admin' },
    { label: 'Налоги' },
  ],
  '/admin/settings': [
    { label: 'Админ', path: '/admin' },
    { label: 'Настройки платформы' },
  ],

  // ── Dev ──
  '/dev/icons': [{ label: 'Dev' }, { label: 'Icons' }],
}

function normalizePathname(pathname: string): string {
  const trimmed = pathname.replace(/\/+$/, '') || '/'
  return trimmed.replace(/\/\d+(?=\/|$)/g, '/:id')
}

export function Topbar() {
  const location = useLocation()
  const navigate = useNavigate()
  const { sidebarMode, toggleSidebar } = usePortalUiStore()
  const isDesktop = useMediaQuery(breakpoints.md)
  const { data: attention } = useAttentionFeed()

  const normalized = normalizePathname(location.pathname)
  const breadcrumbs: Crumb[] = BREADCRUMB_MAP[normalized] ?? [{ label: 'Главная' }]
  const isSidebarOpen = sidebarMode === 'open'
  const bellDot = (attention?.total ?? 0) > 0

  return (
    <header className="h-14 bg-harbor-bg border-b border-border flex items-center gap-3 md:gap-4 px-4 lg:px-6 flex-shrink-0">
      {/* Sidebar toggle */}
      <button
        type="button"
        onClick={() => toggleSidebar(isDesktop)}
        className="p-1 text-text-secondary hover:text-text-primary transition-colors cursor-pointer flex-shrink-0"
        title={isSidebarOpen ? 'Свернуть меню' : 'Развернуть меню'}
        aria-label="Переключить боковое меню"
      >
        <Icon name={isSidebarOpen ? 'close' : 'more-h'} size={20} />
      </button>

      {/* Breadcrumbs — intermediate crumbs with path are clickable Links.
          On mobile (3+ chain), middle crumbs collapse to show First › Last only. */}
      <nav
        aria-label="Хлебные крошки"
        className="flex items-center gap-1 text-sm text-text-secondary min-w-0 flex-1 md:flex-initial overflow-hidden"
      >
        {breadcrumbs.map((crumb, i) => {
          const isLast = i === breadcrumbs.length - 1
          const isFirst = i === 0
          const hideOnMobile = !isLast && !isFirst && breadcrumbs.length > 2
          const isClickable = !isLast && !!crumb.path
          return (
            <span
              key={`${crumb.label}-${i}`}
              className={`flex items-center gap-1 min-w-0 ${hideOnMobile ? 'hidden md:flex' : ''}`}
            >
              {i > 0 && (
                <Icon
                  name="chevron-right"
                  size={11}
                  className="text-text-tertiary flex-shrink-0"
                />
              )}
              {isClickable ? (
                <Link
                  to={crumb.path!}
                  className="truncate rounded-sm hover:text-text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-1 focus-visible:ring-offset-harbor-bg transition-colors cursor-pointer"
                >
                  {crumb.label}
                </Link>
              ) : (
                <span
                  className={`truncate ${isLast ? 'text-text-primary font-medium' : ''}`}
                >
                  {crumb.label}
                </span>
              )}
            </span>
          )
        })}
      </nav>

      {/* Search stub */}
      <div className="hidden md:flex flex-1 max-w-[360px] mx-auto">
        <button
          type="button"
          onClick={() => {
            /* ⌘K palette — stub until §7.14 */
          }}
          className="w-full flex items-center gap-2 px-3 py-1.5 rounded-md bg-harbor-secondary border border-border text-sm text-text-tertiary hover:border-border-active transition-colors cursor-pointer"
          title="Глобальный поиск (в разработке)"
          aria-label="Открыть глобальный поиск"
        >
          <Icon name="search" size={14} />
          <span className="flex-1 text-left">Поиск кампаний, каналов, транзакций…</span>
          <span className="font-mono text-[11px] text-text-tertiary">⌘K</span>
        </button>
      </div>

      {/* Bell */}
      <button
        type="button"
        onClick={() => navigate('/feedback')}
        className="relative p-1.5 rounded-md text-text-secondary hover:text-text-primary hover:bg-harbor-secondary transition-colors cursor-pointer flex-shrink-0"
        aria-label={bellDot ? `Уведомления (есть ${attention?.total ?? 0} новых)` : 'Уведомления'}
      >
        <Icon name="bell" size={18} />
        {bellDot && (
          <span
            aria-hidden="true"
            className="absolute top-1 right-1 w-2 h-2 rounded-full bg-danger ring-2 ring-harbor-bg"
          />
        )}
      </button>
    </header>
  )
}
