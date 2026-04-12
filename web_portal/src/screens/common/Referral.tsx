import { useState } from 'react'
import { Card, Button, EmptyState, Skeleton, Notification, StatusPill } from '@shared/ui'
import { formatDateMSK } from '@/lib/constants'
import { useReferralStats } from '@/hooks/useUserQueries'

export default function Referral() {
  const { data: stats, isLoading: loading, isError } = useReferralStats()
  const [copySuccess, setCopySuccess] = useState(false)

  const handleCopy = async () => {
    if (!stats?.referral_link) return
    try {
      await navigator.clipboard.writeText(stats.referral_link)
      setCopySuccess(true)
      setTimeout(() => setCopySuccess(false), 2000)
    } catch {
      // fallback
    }
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-32" />
        <Skeleton className="h-24" />
        <Skeleton className="h-40" />
      </div>
    )
  }

  if (isError || !stats) {
    return (
      <Notification type="danger">Не удалось загрузить данные о рефералах</Notification>
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-display font-bold text-text-primary">🎁 Реферальная программа</h1>

      {/* Hero */}
      <Card title="Ваша ссылка">
        <p className="text-text-secondary mb-3">
          Приглашайте друзей — получайте кредиты за каждую оплату
        </p>

        <div className="bg-harbor-elevated rounded-lg p-3 mb-3 flex items-center justify-between">
          <code className="text-sm text-accent font-mono">{stats.referral_code}</code>
          <Button
            variant={copySuccess ? 'success' : 'secondary'}
            size="sm"
            onClick={handleCopy}
          >
            {copySuccess ? '✅ Скопировано' : '📋 Копировать'}
          </Button>
        </div>
      </Card>

      {/* Stats */}
      <Card title="Статистика">
        <div className="grid grid-cols-3 gap-3 text-center">
          <div>
            <p className="text-xl font-bold text-accent">{stats.total_referrals}</p>
            <p className="text-xs text-text-tertiary mt-1">Приглашено</p>
          </div>
          <div>
            <p className="text-xl font-bold text-success">{stats.active_referrals}</p>
            <p className="text-xs text-text-tertiary mt-1">Активных</p>
          </div>
          <div>
            <p className="text-xl font-bold text-warning">{Number(stats.total_earned_rub).toFixed(0)} ₽</p>
            <p className="text-xs text-text-tertiary mt-1">Заработано</p>
          </div>
        </div>
      </Card>

      {/* Referrals list */}
      <Card title="Рефералы">
        {stats.referrals.length === 0 ? (
          <EmptyState icon="👥" title="Пока нет рефералов" description="Поделитесь ссылкой с друзьями" />
        ) : (
          <div className="space-y-3">
            {stats.referrals.map((ref) => (
              <div key={ref.id} className="flex items-center gap-3 p-3 bg-harbor-elevated rounded-lg">
                <div className="w-8 h-8 rounded-full bg-accent-muted flex items-center justify-center text-sm font-semibold text-accent">
                  {ref.username?.[0]?.toUpperCase() ?? '👤'}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-text-primary truncate">
                    {ref.username ?? `User #${ref.telegram_id}`}
                  </p>
                  <p className="text-xs text-text-tertiary">
                    {formatDateMSK(ref.created_at)}
                  </p>
                </div>
                <StatusPill status={ref.is_active ? 'success' : 'default'}>
                  {ref.is_active ? 'Активен' : 'Новый'}
                </StatusPill>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* How it works */}
      <Card title="Как это работает">
        <ol className="space-y-2 text-sm text-text-secondary list-decimal list-inside">
          <li>Поделитесь ссылкой с другом</li>
          <li>Друг регистрируется по вашей ссылке</li>
          <li>После первого пополнения вы получаете бонусные кредиты</li>
          <li>Без ограничений — приглашайте сколько угодно</li>
        </ol>
      </Card>
    </div>
  )
}
