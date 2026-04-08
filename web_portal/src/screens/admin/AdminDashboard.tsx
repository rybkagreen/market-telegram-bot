import { useNavigate } from 'react-router-dom'
import { Card, Skeleton, Notification } from '@shared/ui'
import { formatCurrency } from '@/lib/constants'
import { usePlatformStats } from '@/hooks/useAdminQueries'

export default function AdminDashboard() {
  const navigate = useNavigate()
  const { data: stats, isLoading, error } = usePlatformStats()

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-24" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-28" />)}
        </div>
      </div>
    )
  }

  if (error || !stats) {
    return (
      <Notification type="danger">
        Не удалось загрузить статистику платформы.
        {error && <div className="text-xs text-text-tertiary mt-1">{error.message}</div>}
      </Notification>
    )
  }

  return (
    <div className="space-y-6">
      {/* Page title */}
      <div>
        <h1 className="text-2xl font-display font-bold text-text-primary">Панель администратора</h1>
        <p className="text-text-secondary mt-1">Общая статистика платформы RekHarbor</p>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-4">
          <p className="text-sm text-text-secondary">👥 Пользователи</p>
          <p className="text-3xl font-bold text-text-primary mt-2">{stats.users.total}</p>
          <div className="flex gap-3 mt-2 text-xs text-text-tertiary">
            <span>Активных: {stats.users.active}</span>
            <span>Админов: {stats.users.admins}</span>
          </div>
        </Card>

        <Card className="p-4">
          <p className="text-sm text-text-secondary">📍 Размещения</p>
          <p className="text-3xl font-bold text-text-primary mt-2">{stats.placements.total}</p>
          <div className="flex gap-3 mt-2 text-xs text-text-tertiary">
            <span>Активных: {stats.placements.active}</span>
            <span>Завершённых: {stats.placements.completed}</span>
          </div>
        </Card>

        <Card className="p-4">
          <p className="text-sm text-text-secondary">⚖️ Споры</p>
          <p className="text-3xl font-bold text-text-primary mt-2">{stats.disputes.total}</p>
          <div className="flex gap-3 mt-2 text-xs text-text-tertiary">
            <span className="text-warning">Открытых: {stats.disputes.open}</span>
            <span className="text-success">Решённых: {stats.disputes.resolved}</span>
          </div>
        </Card>

        <Card className="p-4">
          <p className="text-sm text-text-secondary">💬 Обращения</p>
          <p className="text-3xl font-bold text-text-primary mt-2">{stats.feedback.total}</p>
          <div className="flex gap-3 mt-2 text-xs text-text-tertiary">
            <span className="text-warning">Новых: {stats.feedback.new}</span>
            <span className="text-success">Решённых: {stats.feedback.resolved}</span>
          </div>
        </Card>
      </div>

      {/* Financial section */}
      <Card title="💰 Финансы платформы" className="p-0 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="sr-only">
              <tr>
                <th scope="col">Параметр</th>
                <th scope="col">Сумма</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              <tr>
                <th scope="row" className="px-5 py-3 text-text-secondary font-normal">Внесено всего</th>
                <td className="px-5 py-3 text-right font-mono text-text-primary">{formatCurrency(stats.financial.total_topups)}</td>
              </tr>
              <tr>
                <th scope="row" className="px-5 py-3 text-text-secondary font-normal">Выведено всего</th>
                <td className="px-5 py-3 text-right font-mono text-text-primary">{formatCurrency(stats.financial.total_payouts)}</td>
              </tr>
              <tr className="bg-harbor-elevated/50">
                <th scope="row" className="px-5 py-3 text-text-secondary font-normal">Оборот (внесено − выведено)</th>
                <td className="px-5 py-3 text-right font-mono font-bold text-text-primary">{formatCurrency(stats.financial.net_balance)}</td>
              </tr>
              <tr><td colSpan={2} className="px-5 border-t border-border" /></tr>
              <tr>
                <th scope="row" className="px-5 py-3 text-text-secondary font-normal">🔒 В эскроу</th>
                <td className="px-5 py-3 text-right font-mono text-text-secondary">{formatCurrency(stats.financial.escrow_reserved)}</td>
              </tr>
              <tr>
                <th scope="row" className="px-5 py-3 text-text-secondary font-normal">⏳ Ожидают вывода</th>
                <td className="px-5 py-3 text-right font-mono text-text-secondary">{formatCurrency(stats.financial.payout_reserved)}</td>
              </tr>
              <tr className="bg-accent-muted/30">
                <th scope="row" className="px-5 py-3 text-text-secondary font-normal">⭐ Комиссия платформы</th>
                <td className="px-5 py-3 text-right font-mono font-bold text-accent">{formatCurrency(stats.financial.profit_accumulated)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </Card>

      {/* Quick actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="p-4 cursor-pointer hover:bg-harbor-elevated transition-colors" onClick={() => navigate('/admin/users')}>
          <p className="text-lg font-semibold text-text-primary">👥 Пользователи</p>
          <p className="text-sm text-text-tertiary mt-1">Управление пользователями и балансами</p>
        </Card>
        <Card className="p-4 cursor-pointer hover:bg-harbor-elevated transition-colors" onClick={() => navigate('/admin/feedback')}>
          <p className="text-lg font-semibold text-text-primary">💬 Обращения</p>
          <p className="text-sm text-text-tertiary mt-1">{stats.feedback.new} новых обращений</p>
        </Card>
        <Card className="p-4 cursor-pointer hover:bg-harbor-elevated transition-colors" onClick={() => navigate('/admin/disputes')}>
          <p className="text-lg font-semibold text-text-primary">⚖️ Споры</p>
          <p className="text-sm text-text-tertiary mt-1">{stats.disputes.open} открытых споров</p>
        </Card>
      </div>
    </div>
  )
}
