import { useNavigate } from 'react-router-dom'
import { Icon, type IconName } from '@shared/ui'

interface Action {
  id: string
  label: string
  sub: string
  icon: IconName
  tone: 'primary' | 'primary2' | 'secondary'
  href: string
}

interface QuickActionsProps {
  role?: 'advertiser' | 'owner'
}

const ADVERTISER_ACTIONS: Action[] = [
  { id: 'topup', label: 'Пополнить баланс', sub: 'мин. 500 ₽', icon: 'topup', tone: 'primary', href: '/topup' },
  { id: 'campaign', label: 'Создать кампанию', sub: 'рекламная закупка', icon: 'campaign', tone: 'primary2', href: '/adv/campaigns/new/category' },
  { id: 'history', label: 'История транзакций', sub: 'пополнения, платежи', icon: 'docs', tone: 'secondary', href: '/billing/history' },
  { id: 'referral', label: 'Реферальная', sub: 'пригласи друзей', icon: 'referral', tone: 'secondary', href: '/referral' },
  { id: 'legal', label: 'Юридический профиль', sub: 'реквизиты, документы', icon: 'verified', tone: 'secondary', href: '/legal-profile/view' },
  { id: 'contracts', label: 'Мои договоры', sub: 'просмотр и подписание', icon: 'contract', tone: 'secondary', href: '/contracts' },
]

const OWNER_ACTIONS: Action[] = [
  { id: 'add-channel', label: 'Добавить канал', sub: 'подключи к бирже', icon: 'channels', tone: 'primary', href: '/own/channels/add' },
  { id: 'payout', label: 'Запросить выплату', sub: 'вывести заработок', icon: 'payouts', tone: 'primary2', href: '/own/payouts/request' },
  { id: 'requests', label: 'Размещения', sub: 'заявки рекламодателей', icon: 'placement', tone: 'secondary', href: '/own/requests' },
  { id: 'analytics', label: 'Аналитика', sub: 'метрики каналов', icon: 'analytics', tone: 'secondary', href: '/own/analytics' },
  { id: 'legal', label: 'Юр. профиль', sub: 'реквизиты для выплат', icon: 'verified', tone: 'secondary', href: '/legal-profile/view' },
  { id: 'docs', label: 'Документы', sub: 'акты и договоры', icon: 'docs', tone: 'secondary', href: '/acts' },
]

function ActionTile({ action }: { action: Action }) {
  const navigate = useNavigate()
  const iconBg =
    action.tone === 'primary'
      ? 'bg-accent-muted text-accent'
      : action.tone === 'primary2'
        ? 'bg-accent-2-muted text-accent-2'
        : 'bg-harbor-secondary text-text-secondary'
  const borderClr = action.tone === 'primary' ? 'border-accent-muted' : 'border-border'

  return (
    <button
      type="button"
      onClick={() => navigate(action.href)}
      className={`group flex items-center gap-3 p-3 rounded-lg bg-harbor-secondary border ${borderClr} text-left transition-all hover:bg-harbor-elevated hover:-translate-y-0.5 cursor-pointer`}
    >
      <div className={`w-[34px] h-[34px] rounded-md grid place-items-center flex-shrink-0 ${iconBg}`}>
        <Icon name={action.icon} size={17} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-[13px] font-semibold text-text-primary truncate">{action.label}</div>
        <div className="text-[11px] text-text-tertiary truncate mt-0.5">{action.sub}</div>
      </div>
      <Icon name="chevron-right" size={13} className="text-text-tertiary" />
    </button>
  )
}

export function QuickActions({ role = 'advertiser' }: QuickActionsProps) {
  const actions = role === 'owner' ? OWNER_ACTIONS : ADVERTISER_ACTIONS
  return (
    <section className="rounded-xl bg-harbor-card border border-border p-4">
      <h3 className="font-display text-[15px] font-semibold text-text-primary px-1 mb-3">
        Быстрые действия
      </h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
        {actions.map((a) => (
          <ActionTile key={a.id} action={a} />
        ))}
      </div>
    </section>
  )
}
