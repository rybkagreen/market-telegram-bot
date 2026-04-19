import { useNavigate } from 'react-router-dom'
import { Icon, type IconName } from '@shared/ui'
import { useAttentionFeed } from '@/hooks/useUserQueries'
import type { AttentionItem, AttentionSeverity, AttentionType } from '@/api/users'

const SEVERITY_STYLES: Record<AttentionSeverity, { icon: string; text: string }> = {
  danger: { icon: 'bg-danger-muted text-danger', text: 'text-danger' },
  warning: { icon: 'bg-warning-muted text-warning', text: 'text-warning' },
  info: { icon: 'bg-info-muted text-info', text: 'text-info' },
  success: { icon: 'bg-success-muted text-success', text: 'text-success' },
}

const ICON_BY_TYPE: Record<AttentionType, IconName> = {
  legal_profile_incomplete: 'warning',
  placement_pending_approval: 'hourglass',
  new_topup_success: 'success',
  channel_verified: 'telegram',
  contract_sign_required: 'contract',
  payout_ready: 'payouts',
  dispute_requires_response: 'chat',
}

function formatRelative(iso: string): string {
  const then = new Date(iso)
  const diffMin = Math.round((Date.now() - then.getTime()) / 60000)
  if (diffMin < 60) return `${Math.max(diffMin, 1)} мин`
  const diffHr = Math.round(diffMin / 60)
  if (diffHr < 24) return `${diffHr} ч`
  const diffDay = Math.round(diffHr / 24)
  if (diffDay === 1) return 'вчера'
  if (diffDay < 7) return `${diffDay} д`
  return then.toLocaleDateString('ru-RU')
}

function Row({ item, onClick }: { item: AttentionItem; onClick: () => void }) {
  const style = SEVERITY_STYLES[item.severity]
  const iconName = ICON_BY_TYPE[item.type] ?? 'info'
  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full flex items-start gap-3 px-4 py-3 text-left border-t border-border first:border-t-0 hover:bg-harbor-secondary transition-colors cursor-pointer"
    >
      <div className={`w-7 h-7 rounded-md grid place-items-center flex-shrink-0 ${style.icon}`}>
        <Icon name={iconName} size={14} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-[12.5px] text-text-primary font-medium leading-snug">
          {item.title}
        </div>
        {item.subtitle && (
          <div className="text-[11px] text-text-tertiary mt-0.5">{item.subtitle}</div>
        )}
      </div>
      <div className="text-[10.5px] text-text-tertiary font-mono flex-shrink-0 mt-1">
        {formatRelative(item.created_at)}
      </div>
    </button>
  )
}

export function NotificationsCard() {
  const navigate = useNavigate()
  const { data, isLoading } = useAttentionFeed()
  const items = data?.items ?? []

  return (
    <section className="rounded-xl bg-harbor-card border border-border overflow-hidden">
      <header className="flex items-center justify-between px-5 py-3.5 border-b border-border">
        <div>
          <h3 className="font-display text-[14px] font-semibold text-text-primary">
            Требует внимания
          </h3>
          <p className="text-[11px] text-text-tertiary mt-0.5">
            {isLoading ? 'Загружаем…' : `${items.length} ${items.length === 1 ? 'событие' : items.length < 5 ? 'события' : 'событий'}`}
          </p>
        </div>
        <button
          type="button"
          className="flex items-center gap-1 text-[12px] text-accent hover:text-accent-hover transition-colors cursor-pointer"
          onClick={() => navigate('/feedback')}
        >
          Все <Icon name="chevron-right" size={12} />
        </button>
      </header>
      <div>
        {isLoading ? (
          <div className="px-5 py-6 text-[12.5px] text-text-tertiary">Загружаем…</div>
        ) : items.length === 0 ? (
          <div className="px-5 py-6 text-[12.5px] text-text-tertiary">
            Всё спокойно — нет новых событий.
          </div>
        ) : (
          items.slice(0, 5).map((item, i) => (
            <Row
              key={`${item.type}-${i}`}
              item={item}
              onClick={() => item.url && navigate(item.url)}
            />
          ))
        )}
      </div>
    </section>
  )
}
