import { useNavigate, useLocation } from 'react-router-dom'
import { Icon } from '@shared/ui'
import { usePortalUiStore } from '@/stores/portalUiStore'
import { useMediaQuery, breakpoints } from '@shared/hooks/useMediaQuery'
import { useAttentionFeed } from '@/hooks/useUserQueries'

const BREADCRUMB_MAP: Record<string, string[]> = {
  '/': ['Главная'],
  '/cabinet': ['Кабинет'],
  '/plans': ['Тариф'],
  '/topup': ['Пополнить баланс'],
  '/topup/confirm': ['Пополнить баланс', 'Подтверждение'],
  '/referral': ['Реферальная программа'],
  '/help': ['Центр помощи'],
  '/feedback': ['Обратная связь'],
  '/billing/history': ['Финансы', 'История транзакций'],
  '/profile/reputation': ['Профиль', 'Репутация'],
  '/acts': ['Мои акты'],
  '/contracts': ['Документы', 'Договоры'],
  '/contracts/:id': ['Документы', 'Договор'],
  '/contracts/framework': ['Документы', 'Рамочный договор'],
  '/legal-profile/view': ['Юридический профиль'],
  '/legal-profile/documents': ['Юридический профиль', 'Документы'],
  '/legal-profile': ['Юридический профиль'],
  '/accept-rules': ['Принять правила'],

  // ── Advertiser ──
  '/adv/campaigns': ['Реклама', 'Мои кампании'],
  '/adv/campaigns/new/category': ['Реклама', 'Новая кампания', 'Категория'],
  '/adv/campaigns/new/channels': ['Реклама', 'Новая кампания', 'Каналы'],
  '/adv/campaigns/new/format': ['Реклама', 'Новая кампания', 'Формат'],
  '/adv/campaigns/new/text': ['Реклама', 'Новая кампания', 'Текст'],
  '/adv/campaigns/new/terms': ['Реклама', 'Новая кампания', 'Условия'],
  '/adv/campaigns/:id/waiting': ['Реклама', 'Кампания', 'Ожидание'],
  '/adv/campaigns/:id/payment': ['Реклама', 'Кампания', 'Оплата'],
  '/adv/campaigns/:id/counter-offer': ['Реклама', 'Кампания', 'Встречное предложение'],
  '/adv/campaigns/:id/published': ['Реклама', 'Кампания', 'Опубликовано'],
  '/adv/campaigns/:id/dispute': ['Реклама', 'Кампания', 'Спор'],
  '/adv/analytics': ['Реклама', 'Аналитика'],
  '/adv/disputes': ['Реклама', 'Споры'],
  '/campaign/:id/ord': ['Реклама', 'Кампания', 'ОРД'],
  '/campaign/video': ['Реклама', 'Видео-креатив'],

  // ── Owner ──
  '/own/channels': ['Каналы', 'Мои каналы'],
  '/own/channels/add': ['Каналы', 'Добавить канал'],
  '/own/channels/:id': ['Каналы', 'Канал'],
  '/own/channels/:id/settings': ['Каналы', 'Канал', 'Настройки'],
  '/own/requests': ['Каналы', 'Размещения'],
  '/own/requests/:id': ['Каналы', 'Размещения', 'Детали'],
  '/own/payouts': ['Каналы', 'Выплаты'],
  '/own/payouts/request': ['Каналы', 'Запрос выплаты'],
  '/own/disputes': ['Каналы', 'Споры'],
  '/own/disputes/:id': ['Каналы', 'Споры', 'Детали'],
  '/own/analytics': ['Каналы', 'Аналитика'],

  // ── Shared disputes ──
  '/disputes/:id': ['Споры', 'Детали'],

  // ── Admin ──
  '/admin': ['Админ-панель'],
  '/admin/users': ['Админ', 'Пользователи'],
  '/admin/users/:id': ['Админ', 'Пользователи', 'Детали'],
  '/admin/disputes': ['Админ', 'Споры'],
  '/admin/disputes/:id': ['Админ', 'Споры', 'Детали'],
  '/admin/feedback': ['Админ', 'Обращения'],
  '/admin/feedback/:id': ['Админ', 'Обращения', 'Детали'],
  '/admin/payouts': ['Админ', 'Выплаты'],
  '/admin/accounting': ['Админ', 'Бухгалтерия'],
  '/admin/tax-summary': ['Админ', 'Налоги'],
  '/admin/settings': ['Админ', 'Настройки платформы'],

  // ── Dev ──
  '/dev/icons': ['Dev', 'Icons'],
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
  const breadcrumbs = BREADCRUMB_MAP[normalized] ?? ['Главная']
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

      {/* Breadcrumbs — on mobile shows first + last, intermediate hidden; on md+ shows full chain */}
      <nav
        aria-label="Хлебные крошки"
        className="flex items-center gap-1 text-sm text-text-secondary min-w-0 flex-1 md:flex-initial overflow-hidden"
      >
        {breadcrumbs.map((crumb, i) => {
          const isLast = i === breadcrumbs.length - 1
          const isFirst = i === 0
          const hideOnMobile = !isLast && !isFirst && breadcrumbs.length > 2
          return (
            <span
              key={`${crumb}-${i}`}
              className={`flex items-center gap-1 min-w-0 ${hideOnMobile ? 'hidden md:flex' : ''}`}
            >
              {i > 0 && (
                <Icon name="chevron-right" size={11} className="text-text-tertiary flex-shrink-0" />
              )}
              <span
                className={`truncate ${isLast ? 'text-text-primary font-medium' : ''}`}
              >
                {crumb}
              </span>
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
