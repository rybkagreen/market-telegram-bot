import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, Button, Notification, Skeleton, StatusPill, Textarea } from '@shared/ui'
import { formatDateTimeMSK } from '@/lib/constants'
import { useDisputeById, useResolveDispute } from '@/hooks/useDisputeQueries'

type Resolution = 'owner_fault' | 'advertiser_fault' | 'technical' | 'partial'

const RESOLUTION_DESC: Record<Resolution, string> = {
  owner_fault: 'Полный возврат рекламодателю (100%), владельцу 0%',
  advertiser_fault: 'Без возврата рекламодателю (0%), владельцу 100%',
  technical: 'Полный возврат рекламодателю (100%), платформa покрывает убыток',
  partial: 'Частичный возврат',
}

export default function AdminDisputeDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const disputeId = id ? Number(id) : null

  const { data: dispute, isLoading: loading, isError } = useDisputeById(disputeId)
  const resolveMutation = useResolveDispute()

  const [resolution, setResolution] = useState<Resolution | null>(null)
  const [adminComment, setAdminComment] = useState('')
  const [customSplit, setCustomSplit] = useState(50)
  const [error, setError] = useState<string | null>(null)

  const handleResolve = () => {
    if (!disputeId || !resolution) return
    resolveMutation.mutate(
      {
        id: disputeId,
        resolution,
        adminComment: adminComment || undefined,
        customSplitPercent: resolution === 'partial' ? customSplit : undefined,
      },
      {
        onSuccess: () => navigate('/admin/disputes'),
        onError: () => setError('Ошибка при разрешении спора'),
      },
    )
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-20" />
        <Skeleton className="h-40" />
      </div>
    )
  }

  if (isError || !dispute) {
    return <Notification type="danger">{error ?? 'Спор не найден'}</Notification>
  }

  const statusColor: Record<string, 'success' | 'warning' | 'danger' | 'default'> = {
    open: 'danger',
    owner_explained: 'warning',
    resolved: 'success',
    closed: 'default',
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-display font-bold text-text-primary">Спор #{dispute.id}</h1>
        <Button variant="secondary" size="sm" onClick={() => navigate('/admin/disputes')}>← Назад</Button>
      </div>

      <Card>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-text-secondary">Статус</span>
            <StatusPill status={statusColor[dispute.status] ?? 'default'}>{dispute.status}</StatusPill>
          </div>
          <div className="flex justify-between">
            <span className="text-text-secondary">Причина</span>
            <span className="text-text-primary">{dispute.reason.replace(/_/g, ' ')}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-secondary">Создан</span>
            <span className="text-text-primary">{formatDateTimeMSK(dispute.created_at)}</span>
          </div>
        </div>
      </Card>

      {/* Parties */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card title="Рекламодатель">
          <p className="text-sm font-medium text-text-primary">User #{dispute.advertiser_id}</p>
          {dispute.advertiser_comment && (
            <p className="text-sm text-text-secondary mt-2">{dispute.advertiser_comment}</p>
          )}
        </Card>
        <Card title="Владелец">
          <p className="text-sm font-medium text-text-primary">User #{dispute.owner_id}</p>
          {dispute.owner_explanation && (
            <p className="text-sm text-text-secondary mt-2">{dispute.owner_explanation}</p>
          )}
        </Card>
      </div>

      {dispute.resolution ? (
        <Card title="Решение">
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-text-secondary">Решение</span>
              <span className="text-text-primary font-semibold">{dispute.resolution.replace(/_/g, ' ')}</span>
            </div>
            {dispute.resolution_comment && (
              <div className="flex justify-between">
                <span className="text-text-secondary">Комментарий</span>
                <span className="text-text-primary">{dispute.resolution_comment}</span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-text-secondary">Возврат рекламодателю</span>
              <span className="text-text-primary">{dispute.advertiser_refund_pct}%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-secondary">Выплата владельцу</span>
              <span className="text-text-primary">{dispute.owner_payout_pct}%</span>
            </div>
          </div>
        </Card>
      ) : (
        <>
          <Card title="Разрешить спор">
            <div className="space-y-3">
              <div className="flex gap-2 flex-wrap">
                {(['owner_fault', 'advertiser_fault', 'technical', 'partial'] as Resolution[]).map((res) => (
                  <Button
                    key={res}
                    variant={resolution === res ? 'primary' : 'secondary'}
                    size="sm"
                    onClick={() => setResolution(res)}
                  >
                    {res.replace(/_/g, ' ')}
                  </Button>
                ))}
              </div>

              {resolution && (
                <p className="text-sm text-text-secondary">{RESOLUTION_DESC[resolution]}</p>
              )}

              {resolution === 'partial' && (
                <div className="space-y-2">
                  <label className="block text-sm text-text-secondary">
                    Возврат рекламодателю: {customSplit}%
                  </label>
                  <input
                    type="range"
                    min={0}
                    max={100}
                    value={customSplit}
                    onChange={(e) => setCustomSplit(Number(e.target.value))}
                    className="w-full accent-accent"
                  />
                  <div className="flex justify-between text-xs text-text-tertiary">
                    <span>Рекламодатель: {customSplit}%</span>
                    <span>Владелец: {100 - customSplit}%</span>
                  </div>
                </div>
              )}

              <Textarea
                rows={3}
                value={adminComment}
                onChange={setAdminComment}
                placeholder="Комментарий администратора (необязательно)"
              />

              <Button
                variant="primary"
                fullWidth
                loading={resolveMutation.isPending}
                disabled={!resolution || resolveMutation.isPending}
                onClick={handleResolve}
              >
                {resolveMutation.isPending ? 'Разрешение...' : 'Разрешить спор'}
              </Button>
            </div>
          </Card>
        </>
      )}
    </div>
  )
}
