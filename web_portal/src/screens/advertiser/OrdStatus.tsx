import { useParams, useNavigate } from 'react-router-dom'
import { Card, Button, Skeleton, StatusPill, Notification as AppNotification } from '@shared/ui'
import { useOrdStatus } from '@/hooks/useOrdQueries'
import type { OrdStatus } from '@/lib/types/billing'

const statusMap: Record<OrdStatus, { label: string; variant: 'warning' | 'info' | 'success' | 'danger' }> = {
  pending:        { label: '⏳ ОРД-регистрация', variant: 'warning' },
  registered:     { label: '🔄 Регистрация принята ОРД', variant: 'info' },
  token_received: { label: '✅ ERID получен', variant: 'success' },
  reported:       { label: '📨 Отчёт отправлен в ОРД', variant: 'success' },
  failed:         { label: '❌ Ошибка ОРД', variant: 'danger' },
}

export default function OrdStatus() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const placementId = id ? Number(id) : null

  const { data: ordData, isLoading, error } = useOrdStatus(placementId)

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-display font-bold text-text-primary">Статус ОРД</h1>
        <Card title={id ? `Заявка #${id}` : 'Заявка'}>
          <Skeleton className="h-16" />
        </Card>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-display font-bold text-text-primary">Статус ОРД</h1>
        <AppNotification type="error">
          <span className="text-sm">Не удалось загрузить статус ОРД</span>
        </AppNotification>
        <Button variant="secondary" fullWidth onClick={() => navigate(-1 as unknown as string)}>
          ← Назад
        </Button>
      </div>
    )
  }

  const statusInfo = ordData ? statusMap[ordData.status] : null

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-display font-bold text-text-primary">Статус ОРД</h1>

      <Card title={id ? `Заявка #${id}` : 'Заявка'}>
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-text-secondary">Статус</span>
            {statusInfo ? (
              <StatusPill status={statusInfo.variant}>{statusInfo.label}</StatusPill>
            ) : (
              <span className="text-text-tertiary">—</span>
            )}
          </div>
          {ordData?.erid && (
            <div className="flex items-center justify-between">
              <span className="text-text-secondary">ERID</span>
              <span className="text-text-tertiary font-mono text-sm">{ordData.erid}</span>
            </div>
          )}
          {ordData?.ord_provider && (
            <div className="flex items-center justify-between">
              <span className="text-text-secondary">Оператор</span>
              <span className="text-text-tertiary">{ordData.ord_provider}</span>
            </div>
          )}
          {ordData?.error_message && (
            <div className="flex items-center justify-between">
              <span className="text-text-secondary">Ошибка</span>
              <span className="text-text-danger text-sm">{ordData.error_message}</span>
            </div>
          )}
        </div>
      </Card>

      <AppNotification type="info">
        <span className="text-sm">
          Регистрация в ОРД (Оператор рекламных данных) — обязательный шаг для маркировки рекламы.
          Автоматическая регистрация происходит после публикации.
        </span>
      </AppNotification>

      <Button variant="secondary" fullWidth onClick={() => navigate(-1 as unknown as string)}>
        ← Назад
      </Button>
    </div>
  )
}
