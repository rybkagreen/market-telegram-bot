import { useNavigate } from 'react-router-dom'
import {
  Skeleton,
  Notification,
  Icon,
  ScreenHeader,
  FeeBreakdown,
} from '@shared/ui'
import type { IconName } from '@shared/ui'
import { formatCurrency } from '@/lib/constants'
import { usePlatformStats } from '@/hooks/useAdminQueries'

export default function AdminDashboard() {
  const navigate = useNavigate()
  const { data: stats, isLoading, error } = usePlatformStats()

  if (isLoading) {
    return (
      <div className="max-w-[1280px] mx-auto space-y-4">
        <Skeleton className="h-16" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
        <Skeleton className="h-64" />
      </div>
    )
  }

  if (error || !stats) {
    return (
      <div className="max-w-[1280px] mx-auto">
        <Notification type="danger">
          Не удалось загрузить статистику платформы.
          {error && <div className="text-xs text-text-tertiary mt-1">{error.message}</div>}
        </Notification>
      </div>
    )
  }

  return (
    <div className="max-w-[1280px] mx-auto">
      <ScreenHeader
        title="Панель администратора"
        subtitle="Общая статистика платформы RekHarbor — пользователи, размещения, споры, финансы"
      />

      <div
        className="grid gap-3.5 mb-5"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))' }}
      >
        <KpiTile
          icon="users"
          tone="accent"
          label="Пользователи"
          value={String(stats.users.total)}
          delta={`Активных ${stats.users.active} · админов ${stats.users.admins}`}
        />
        <KpiTile
          icon="placement"
          tone="accent2"
          label="Размещения"
          value={String(stats.placements.total)}
          delta={`Активных ${stats.placements.active} · завершено ${stats.placements.completed}`}
        />
        <KpiTile
          icon="disputes"
          tone="warning"
          label="Споры"
          value={String(stats.disputes.total)}
          delta={`Открытых ${stats.disputes.open} · решено ${stats.disputes.resolved}`}
        />
        <KpiTile
          icon="feedback"
          tone="info"
          label="Обращения"
          value={String(stats.feedback.total)}
          delta={`Новых ${stats.feedback.new} · решено ${stats.feedback.resolved}`}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr] mb-5">
        <div className="bg-harbor-card border border-border rounded-xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <Icon name="wallet" size={14} className="text-text-tertiary" />
            <span className="font-display text-[14px] font-semibold text-text-primary">
              Финансы платформы
            </span>
          </div>

          <div className="grid gap-3 sm:grid-cols-3 mb-4">
            <FinTile
              icon="deposit"
              tone="success"
              label="Внесено всего"
              value={formatCurrency(stats.financial.total_topups)}
            />
            <FinTile
              icon="withdraw"
              tone="danger"
              label="Выведено всего"
              value={formatCurrency(stats.financial.total_payouts)}
            />
            <FinTile
              icon="wave"
              tone="accent"
              label="Нетто"
              value={formatCurrency(stats.financial.net_balance)}
            />
          </div>

          <FeeBreakdown
            rows={[
              {
                label: 'В эскроу',
                value: formatCurrency(stats.financial.escrow_reserved),
              },
              {
                label: 'Ожидают вывода',
                value: formatCurrency(stats.financial.payout_reserved),
              },
            ]}
            total={{
              label: 'Комиссия платформы (накоплено)',
              value: formatCurrency(stats.financial.profit_accumulated),
            }}
          />
        </div>

        <div className="bg-harbor-card border border-border rounded-xl p-5 flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <Icon name="zap" size={14} className="text-accent" />
            <span className="font-display text-[14px] font-semibold text-text-primary">
              Быстрые действия
            </span>
          </div>

          <QuickAction
            icon="users"
            title="Пользователи"
            description="Управление балансами, ролями, блокировками"
            onClick={() => navigate('/admin/users')}
          />
          <QuickAction
            icon="disputes"
            title="Споры"
            description={`${stats.disputes.open} открытых споров`}
            onClick={() => navigate('/admin/disputes')}
          />
          <QuickAction
            icon="feedback"
            title="Обращения"
            description={`${stats.feedback.new} новых обращений`}
            onClick={() => navigate('/admin/feedback')}
          />
          <QuickAction
            icon="payouts"
            title="Выплаты"
            description="Очередь ручных выплат владельцам"
            onClick={() => navigate('/admin/payouts')}
          />
        </div>
      </div>
    </div>
  )
}

const toneIconBg: Record<'success' | 'warning' | 'accent' | 'accent2' | 'info' | 'danger', string> = {
  success: 'bg-success-muted text-success',
  warning: 'bg-warning-muted text-warning',
  accent: 'bg-accent-muted text-accent',
  accent2: 'bg-accent-2-muted text-accent-2',
  info: 'bg-info-muted text-info',
  danger: 'bg-danger-muted text-danger',
}

function KpiTile({
  icon,
  tone,
  label,
  value,
  delta,
}: {
  icon: IconName
  tone: 'success' | 'warning' | 'accent' | 'accent2' | 'info'
  label: string
  value: string
  delta: string
}) {
  return (
    <div className="bg-harbor-card border border-border rounded-xl p-[18px] flex gap-3.5 items-start">
      <span
        className={`grid place-items-center w-[42px] h-[42px] rounded-[10px] flex-shrink-0 ${toneIconBg[tone]}`}
      >
        <Icon name={icon} size={18} />
      </span>
      <div className="flex-1 min-w-0">
        <div className="text-[11px] font-semibold uppercase tracking-wider text-text-tertiary mb-1">
          {label}
        </div>
        <div className="font-display text-xl font-bold text-text-primary tracking-[-0.02em] tabular-nums truncate">
          {value}
        </div>
        <div className="text-[11.5px] text-text-tertiary mt-0.5 truncate">{delta}</div>
      </div>
    </div>
  )
}

function FinTile({
  icon,
  tone,
  label,
  value,
}: {
  icon: IconName
  tone: 'success' | 'danger' | 'accent'
  label: string
  value: string
}) {
  return (
    <div className="bg-harbor-secondary border border-border rounded-[10px] p-3 flex gap-3 items-center">
      <span className={`grid place-items-center w-9 h-9 rounded-md flex-shrink-0 ${toneIconBg[tone]}`}>
        <Icon name={icon} size={15} />
      </span>
      <div className="min-w-0">
        <div className="text-[10.5px] uppercase tracking-wider text-text-tertiary">{label}</div>
        <div className="font-mono tabular-nums font-semibold text-text-primary text-[14px] truncate">
          {value}
        </div>
      </div>
    </div>
  )
}

function QuickAction({
  icon,
  title,
  description,
  onClick,
}: {
  icon: IconName
  title: string
  description: string
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="text-left bg-harbor-secondary border border-border rounded-[10px] p-3.5 flex items-center gap-3 hover:border-accent/40 transition-colors"
    >
      <span className="grid place-items-center w-9 h-9 rounded-md bg-accent-muted text-accent flex-shrink-0">
        <Icon name={icon} size={14} />
      </span>
      <div className="flex-1 min-w-0">
        <div className="font-display text-[13.5px] font-semibold text-text-primary">{title}</div>
        <div className="text-[12px] text-text-tertiary truncate">{description}</div>
      </div>
      <Icon name="chevron-right" size={13} className="text-text-tertiary" />
    </button>
  )
}
