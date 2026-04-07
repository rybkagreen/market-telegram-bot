import { useParams, useNavigate } from 'react-router-dom'
import { Card, Notification, Button, Skeleton, StatusBadge } from '@shared/ui'
import { formatCurrency } from '@/lib/constants'
import { useDisputeById, useReplyToDispute } from '@/hooks/useDisputeQueries'
import { useState } from 'react'

export default function DisputeDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const numId = id ? parseInt(id, 10) : null
  const { data: dispute, isLoading } = useDisputeById(numId)
  const replyMutation = useReplyToDispute()
  const [replyText, setReplyText] = useState('')

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-12" />
        <Skeleton className="h-32" />
        <Skeleton className="h-24" />
      </div>
    )
  }

  if (!dispute) {
    return <Notification type="danger">Спор не найден</Notification>
  }

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Header */}
      <div className="flex items-center gap-4">
        <div>
          <h1 className="text-2xl font-display font-bold text-text-primary">Спор #{dispute.id}</h1>
          <p className="text-text-secondary mt-1">
            @{dispute.placement?.channel?.username ?? `#${dispute.placement_id}`}
          </p>
        </div>
        <StatusBadge status={dispute.status} />
      </div>

      {/* Placement info */}
      {dispute.placement && (
        <Card title="Информация о размещении">
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-text-secondary">Текст рекламы</span>
              <span className="text-text-primary">{dispute.placement.ad_text.slice(0, 80)}...</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-secondary">Сумма</span>
              <span className="font-mono text-text-primary">{formatCurrency(dispute.placement.proposed_price)}</span>
            </div>
          </div>
        </Card>
      )}

      {/* Dispute details */}
      <Card title="Детали спора">
        <div className="space-y-3">
          <div>
            <p className="text-sm text-text-secondary mb-1">Причина</p>
            <p className="text-text-primary">{dispute.reason}</p>
          </div>
          <div>
            <p className="text-sm text-text-secondary mb-1">Комментарий рекламодателя</p>
            <p className="text-text-primary">{dispute.advertiser_comment}</p>
          </div>
          {dispute.owner_comment && (
            <div>
              <p className="text-sm text-text-secondary mb-1">Ваш ответ</p>
              <p className="text-text-primary">{dispute.owner_comment}</p>
            </div>
          )}
          {dispute.resolution && (
            <div className="bg-success-muted rounded-md p-3">
              <p className="text-sm text-success">✅ Разрешение: {dispute.resolution}</p>
            </div>
          )}
        </div>
      </Card>

      {/* Reply form */}
      {dispute.status === 'open' && (
        <Card title="Ваш ответ">
          <div className="space-y-3">
            <textarea
              className="w-full px-3 py-2 rounded-md border border-border-active bg-harbor-elevated text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent resize-none"
              placeholder="Объясните вашу позицию..."
              rows={4}
              value={replyText}
              onChange={(e) => setReplyText(e.target.value)}
            />
            <Button
              loading={replyMutation.isPending}
              disabled={!replyText.trim() || replyMutation.isPending}
              onClick={() => {
                replyMutation.mutate({ id: dispute.id, comment: replyText }, {
                  onSuccess: () => setReplyText(''),
                })
              }}
            >
              Отправить ответ
            </Button>
          </div>
        </Card>
      )}

      {/* Back button */}
      <Button variant="ghost" fullWidth onClick={() => navigate('/own/requests')}>
        ← К размещениям
      </Button>
    </div>
  )
}
