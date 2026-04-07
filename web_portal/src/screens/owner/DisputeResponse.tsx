import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, Button, Notification, StatusPill, Skeleton, Textarea } from '@shared/ui'
import { PUBLICATION_FORMATS } from '@/lib/constants'
import { formatCurrency } from '@/lib/constants'
import { usePlacement } from '@/hooks/useCampaignQueries'

const MIN_REPLY = 20

export default function DisputeResponse() {
  const { id } = useParams()
  const navigate = useNavigate()

  const numId = id ? parseInt(id, 10) : null
  const { data: placement, isLoading } = usePlacement(numId)

  const [ownerReply, setOwnerReply] = useState('')

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-20" />
        <Skeleton className="h-40" />
        <Skeleton className="h-24" />
      </div>
    )
  }

  if (!placement) {
    return <Notification type="danger">Заявка не найдена</Notification>
  }

  const fmt = PUBLICATION_FORMATS[placement.publication_format]

  const handleSubmit = () => {
    // In production: call API to reply to dispute
    alert('Ответ отправлен')
    navigate('/own/requests')
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-display font-bold text-text-primary">
        Спор по заявке #{placement.id}
      </h1>

      <Notification type="warning">
        <span className="text-sm">⚠️ Открытый спор по размещению</span>
      </Notification>

      {/* Dispute details */}
      <Card title="Детали размещения">
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-text-secondary">Канал</span>
            <span className="text-text-primary font-medium">
              @{placement.channel?.username ?? `#${placement.channel_id}`}
            </span>
          </div>
          {fmt && (
            <div className="flex justify-between">
              <span className="text-text-secondary">Формат</span>
              <span className="text-text-primary">{fmt.icon} {fmt.name}</span>
            </div>
          )}
          <div className="flex justify-between">
            <span className="text-text-secondary">Сумма</span>
            <span className="font-mono text-text-primary font-semibold">
              {formatCurrency(placement.proposed_price)}
            </span>
          </div>
          {placement.has_dispute && (
            <div className="flex justify-between">
              <span className="text-text-secondary">Статус спора</span>
              <StatusPill status="danger">Открыт</StatusPill>
            </div>
          )}
        </div>
      </Card>

      {/* Reply form */}
      {placement.status !== 'cancelled' && placement.status !== 'refunded' ? (
        <Card title="Ваше объяснение">
          <Textarea
            rows={4}
            value={ownerReply}
            onChange={setOwnerReply}
            placeholder={`Минимум ${MIN_REPLY} символов. Подробное объяснение поможет быстрее разрешить спор.`}
          />
          <p className="text-xs text-text-tertiary mt-1">{ownerReply.length} / мин. {MIN_REPLY}</p>

          <Notification type="info" className="mt-3">
            <span className="text-sm">
              Подробное и честное объяснение повышает шансы на благоприятное решение
            </span>
          </Notification>

          <Button
            variant="primary"
            fullWidth
            className="mt-4"
            disabled={ownerReply.length < MIN_REPLY}
            onClick={handleSubmit}
          >
            📤 Отправить объяснение
          </Button>
        </Card>
      ) : (
        <Notification type="info">
          <span className="text-sm">Спор по отменённому размещению не требует ответа</span>
        </Notification>
      )}

      <Button variant="secondary" fullWidth onClick={() => navigate('/own/requests')}>
        ← К размещениям
      </Button>
    </div>
  )
}
