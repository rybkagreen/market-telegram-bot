import { useParams, useNavigate } from 'react-router-dom'
import { Card, Button, Skeleton, StatusPill, Notification as AppNotification } from '@shared/ui'

export default function OrdStatus() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-display font-bold text-text-primary">Статус ОРД</h1>

      <Card title={`Заявка #${id}`}>
        <Skeleton className="h-16" />
      </Card>

      <AppNotification type="info">
        <span className="text-sm">
          Регистрация в ОРД (Оператор рекламных данных) — обязательный шаг для маркировки рекламы.
          Маркировка происходит до публикации рекламы.
        </span>
      </AppNotification>

      <Card>
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-text-secondary">Статус</span>
            <StatusPill status="warning">⏳ Ожидает регистрации</StatusPill>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-text-secondary">Токен ОРД</span>
            <span className="text-text-tertiary">—</span>
          </div>
        </div>
      </Card>

      <Button variant="secondary" fullWidth onClick={() => navigate(-1 as unknown as string)}>
        ← Назад
      </Button>
    </div>
  )
}
