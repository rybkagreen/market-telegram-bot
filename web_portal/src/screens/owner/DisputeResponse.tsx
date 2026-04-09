import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, Button, Notification, StatusPill, Skeleton, Textarea } from '@shared/ui'
import { PUBLICATION_FORMATS } from '@/lib/constants'
import { formatCurrency } from '@/lib/constants'
import { usePlacement } from '@/hooks/useCampaignQueries'
import { useDisputeById, useReplyToDispute } from '@/hooks/useDisputeQueries'

const MIN_REPLY = 20

export default function DisputeResponse() {
  const { id } = useParams()
  const navigate = useNavigate()

  const numId = id ? parseInt(id, 10) : null
  const { data: dispute, isLoading: disputeLoading } = useDisputeById(numId)
  const { data: placement, isLoading: placementLoading } = usePlacement(
    dispute ? dispute.placement_request_id : null,
  )
  const { mutate: replyToDispute, isPending } = useReplyToDispute()

  const [ownerReply, setOwnerReply] = useState('')

  const isLoading = disputeLoading || placementLoading

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-20" />
        <Skeleton className="h-40" />
        <Skeleton className="h-24" />
      </div>
    )
  }

  if (!dispute) {
    return <Notification type="danger">Спор не найден</Notification>
  }

  const fmt = placement ? PUBLICATION_FORMATS[placement.publication_format] : null

  const handleSubmit = () => {
    if (ownerReply.length < MIN_REPLY) return
    replyToDispute(
      { id: dispute.id, comment: ownerReply },
      { onSuccess: () => navigate('/own/requests') },
    )
  }

  const statusLabel: Record<string, string> = {
    open: 'Открыт',
    owner_explained: 'Владелец ответил',
    resolved: 'Решён',
    closed: 'Закрыт',
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-display font-bold text-text-primary">
        Спор #{dispute.id}
      </h1>

      <Notification type="warning">
        <span className="text-sm">⚠️ Статус спора: {statusLabel[dispute.status] ?? dispute.status}</span>
      </Notification>

      {/* Dispute details */}
      <Card title="Детали размещения">
        <div className="space-y-2 text-sm">
          {placement && (
            <>
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
                  {formatCurrency(placement.final_price ?? placement.proposed_price)}
                </span>
              </div>
            </>
          )}
          <div className="flex justify-between">
            <span className="text-text-secondary">Статус спора</span>
            <StatusPill
              status={
                dispute.status === 'open'
                  ? 'danger'
                  : dispute.status === 'owner_explained'
                    ? 'warning'
                    : dispute.status === 'resolved'
                      ? 'success'
                      : 'default'
              }
            >
              {statusLabel[dispute.status] ?? dispute.status}
            </StatusPill>
          </div>
        </div>
      </Card>

      {/* Advertiser comment */}
      {dispute.advertiser_comment && (
        <Card title="Комментарий рекламодателя">
          <p className="text-sm text-text-primary">{dispute.advertiser_comment}</p>
        </Card>
      )}

      {/* Reply form */}
      {dispute.status === 'open' ? (
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
            disabled={ownerReply.length < MIN_REPLY || isPending}
            onClick={handleSubmit}
          >
            {isPending ? '⏳ Отправка...' : '📤 Отправить объяснение'}
          </Button>
        </Card>
      ) : dispute.status === 'owner_explained' ? (
        <Notification type="info">
          <span className="text-sm">✅ Ваше объяснение отправлено. Ожидание решения администратора.</span>
        </Notification>
      ) : (
        <Notification type="info">
          <span className="text-sm">Спор {statusLabel[dispute.status] ?? 'закрыт'}</span>
        </Notification>
      )}

      <Button variant="secondary" fullWidth onClick={() => navigate('/own/requests')}>
        ← К размещениям
      </Button>
    </div>
  )
}
