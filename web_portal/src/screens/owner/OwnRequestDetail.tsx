import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { Card, Notification, Button, Skeleton } from '@shared/ui'
import { formatCurrency } from '@/lib/constants'
import { usePlacementRequest, useUpdatePlacement } from '@/hooks/useCampaignQueries'

export default function OwnRequestDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const numId = id ? parseInt(id, 10) : null

  const { data: request, isLoading } = usePlacementRequest(numId)
  const { mutate: updatePlacement, isPending } = useUpdatePlacement()
  const queryClient = useQueryClient()

  const [counterPrice, setCounterPrice] = useState('')
  const [counterDate, setCounterDate] = useState('')
  const [counterTime, setCounterTime] = useState('14:00')
  const [rejectionText, setRejectionText] = useState('')

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-12" />
        <Skeleton className="h-32" />
        <Skeleton className="h-40" />
      </div>
    )
  }

  if (!request) {
    return <Notification type="danger">Заявка не найдена</Notification>
  }

  const formatNames: Record<string, string> = {
    post_24h: 'Пост 24ч',
    post_48h: 'Пост 48ч',
    post_7d: 'Пост 7д',
    pin_24h: 'Закреп 24ч',
    pin_48h: 'Закреп 48ч',
  }
  const fmtName = formatNames[request.publication_format] ?? request.publication_format
  const isExpired = request.expires_at ? new Date(request.expires_at) < new Date() : false

  const handleAccept = () => {
    updatePlacement({ id: request.id, data: { action: 'accept' } }, {
      onSuccess: () => navigate('/own/requests'),
    })
  }

  const handleCounter = () => {
    const price = parseFloat(counterPrice) || parseFloat(request.proposed_price)
    const schedule = counterDate && counterTime ? `${counterDate}T${counterTime}:00` : undefined
    updatePlacement({ id: request.id, data: { action: 'counter', price, schedule } }, {
      onSuccess: () => navigate('/own/requests'),
      onError: () => {
        queryClient.invalidateQueries({ queryKey: ['placement-request', numId] })
      },
    })
  }

  const handleReject = () => {
    updatePlacement({ id: request.id, data: { action: 'reject', comment: rejectionText } }, {
      onSuccess: () => navigate('/own/requests'),
    })
  }

  // Status banner
  const statusBanner = () => {
    if (isExpired && request.status === 'pending_owner') {
      return <Notification type="danger">⏰ Срок ответа истёк</Notification>
    }
    if (request.status === 'pending_payment') {
      return <Notification type="warning">💳 Ожидаем оплаты от рекламодателя</Notification>
    }
    if (request.status === 'escrow') {
      return <Notification type="success">✅ Оплата получена. Публикация запланирована</Notification>
    }
    if (request.status === 'counter_offer') {
      return <Notification type="info">⏳ Ожидаем ответа рекламодателя на контрпредложение</Notification>
    }
    return null
  }

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-display font-bold text-text-primary">Заявка #{request.id}</h1>
        <p className="text-text-secondary mt-1">
          @{request.channel?.username ?? `#${request.channel_id}`} · {fmtName}
        </p>
      </div>

      {statusBanner()}

      {/* Request details */}
      <Card title="Детали заявки">
        <div className="space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="text-text-secondary">Формат</span>
            <span className="text-text-primary">{fmtName}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-secondary">Предложенная цена</span>
            <span className="font-mono text-accent font-bold">{formatCurrency(request.proposed_price)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-secondary">К выплате (85%)</span>
            <span className="font-mono text-success">{formatCurrency(parseFloat(request.proposed_price) * 0.85)}</span>
          </div>
        </div>
      </Card>

      {/* Ad text */}
      <Card title="Текст объявления">
        <p className="text-text-primary text-sm whitespace-pre-wrap">{request.ad_text}</p>
      </Card>

      {/* Actions for pending_owner */}
      {request.status === 'pending_owner' && !isExpired && (
        <div className="space-y-4">
          <Button variant="success" fullWidth loading={isPending} onClick={handleAccept}>
            ✅ Принять условия
          </Button>

          {/* Counter offer */}
          <Card title="Контр-предложение">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="block text-xs text-text-secondary mb-1">Цена</label>
                <input
                  type="number"
                  className="w-full px-3 py-2 rounded-md border border-border-active bg-harbor-elevated text-text-primary focus:outline-none focus:ring-2 focus:ring-accent"
                  value={counterPrice || request.proposed_price}
                  onChange={(e) => setCounterPrice(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-xs text-text-secondary mb-1">Дата</label>
                <input
                  type="date"
                  className="w-full px-3 py-2 rounded-md border border-border-active bg-harbor-elevated text-text-primary focus:outline-none focus:ring-2 focus:ring-accent"
                  value={counterDate}
                  onChange={(e) => setCounterDate(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-xs text-text-secondary mb-1">Время</label>
                <input
                  type="time"
                  className="w-full px-3 py-2 rounded-md border border-border-active bg-harbor-elevated text-text-primary focus:outline-none focus:ring-2 focus:ring-accent"
                  value={counterTime}
                  onChange={(e) => setCounterTime(e.target.value)}
                />
              </div>
            </div>
            <Button variant="secondary" fullWidth className="mt-3" loading={isPending} onClick={handleCounter}>
              ✏️ Отправить контр-предложение
            </Button>
          </Card>

          {/* Reject */}
          <Card title="Отклонить">
            <textarea
              className="w-full px-3 py-2 rounded-md border border-border-active bg-harbor-elevated text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent resize-none"
              placeholder="Причина отклонения..."
              rows={3}
              value={rejectionText}
              onChange={(e) => setRejectionText(e.target.value)}
            />
            <p className="text-xs text-warning mt-1">⚠️ Необоснованный отказ: −10 к репутации</p>
            <Button
              variant="danger"
              fullWidth
              className="mt-2"
              disabled={rejectionText.length < 10 || isPending}
              onClick={handleReject}
            >
              ❌ Отклонить заявку
            </Button>
          </Card>
        </div>
      )}

      {/* Published result */}
      {request.status === 'published' && request.published_at && (
        <Card>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-text-secondary">Опубликовано</span>
              <span className="text-text-primary">{new Date(request.published_at).toLocaleString('ru-RU')}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-secondary">Заработано</span>
              <span className="font-mono text-success font-bold">{formatCurrency(parseFloat(request.proposed_price) * 0.85)}</span>
            </div>
          </div>
        </Card>
      )}

      {/* Cancelled */}
      {request.status === 'cancelled' && request.rejection_reason && (
        <Card title="Причина отклонения">
          <p className="text-text-primary text-sm">{request.rejection_reason}</p>
        </Card>
      )}

      <Button variant="ghost" fullWidth onClick={() => navigate('/own/requests')}>
        ← К размещениям
      </Button>
    </div>
  )
}
