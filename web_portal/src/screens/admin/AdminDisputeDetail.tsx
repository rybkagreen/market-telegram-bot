import React, { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, Button, Notification, Skeleton, StatusPill, Textarea } from '@shared/ui'
import { api } from '@shared/api/client'

interface DisputeDetail {
  id: number
  placement_id: number
  advertiser_id: number
  owner_id: number
  reason: string
  comment: string
  status: string
  advertiser_username?: string | null
  owner_username?: string | null
  advertiser_comment?: string | null
  owner_explanation?: string | null
  resolution?: string | null
  resolution_comment?: string | null
  advertiser_refund_pct?: number | null
  owner_payout_pct?: number | null
  resolved_at?: string | null
  created_at: string
}

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

  const [dispute, setDispute] = useState<DisputeDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [resolution, setResolution] = useState<Resolution | null>(null)
  const [adminComment, setAdminComment] = useState('')
  const [customSplit, setCustomSplit] = useState(50)
  const [resolving, setResolving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  React.useEffect(() => {
    if (!id) return
    setLoading(true)
    api.get(`disputes/${id}`)
      .json<DisputeDetail>()
      .then((data) => setDispute(data))
      .catch(() => setError('Спор не найден'))
      .finally(() => setLoading(false))
  }, [id])

  const handleResolve = () => {
    if (!id || !resolution) return
    setResolving(true)
    api.post(`disputes/admin/disputes/${id}/resolve`, {
      json: {
        resolution,
        admin_comment: adminComment || undefined,
        custom_split_percent: resolution === 'partial' ? customSplit : undefined,
      },
    })
      .json<DisputeDetail>()
      .then(() => navigate('/admin/disputes'))
      .catch(() => setError('Ошибка при разрешении спора'))
      .finally(() => setResolving(false))
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-20" />
        <Skeleton className="h-40" />
      </div>
    )
  }

  if (error || !dispute) {
    return <Notification type="danger">Спор не найден</Notification>
  }

  const statusColor: Record<string, 'success' | 'warning' | 'danger' | 'default'> = {
    open: 'danger',
    owner_reply: 'warning',
    resolved: 'success',
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
            <span className="text-text-primary">{new Date(dispute.created_at).toLocaleString('ru-RU')}</span>
          </div>
        </div>
      </Card>

      {/* Parties */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card title="Рекламодатель">
          <p className="text-sm font-medium text-text-primary">
            {dispute.advertiser_username ?? `User #${dispute.advertiser_id}`}
          </p>
          {dispute.advertiser_comment && (
            <p className="text-sm text-text-secondary mt-2">{dispute.advertiser_comment}</p>
          )}
        </Card>
        <Card title="Владелец">
          <p className="text-sm font-medium text-text-primary">
            {dispute.owner_username ?? `User #${dispute.owner_id}`}
          </p>
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
                loading={resolving}
                disabled={!resolution || resolving}
                onClick={handleResolve}
              >
                {resolving ? 'Разрешение...' : 'Разрешить спор'}
              </Button>
            </div>
          </Card>
        </>
      )}
    </div>
  )
}
