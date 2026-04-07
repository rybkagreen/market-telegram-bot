import { useState, useEffect } from 'react'
import { Card, Button, Skeleton, EmptyState, Notification } from '@shared/ui'
import { api } from '@shared/api/client'

interface ActItem {
  id: number
  act_number: string
  act_type: string
  act_date: string
  sign_status: string
  signed_at: string | null
  pdf_url: string | null
  placement_request_id: number
}

const TYPE_LABELS: Record<string, string> = {
  income: '📤 Акт-ИСХ',
  expense: '📥 Акт-ВХ',
}

const STATUS_LABELS: Record<string, string> = {
  draft: 'Черновик',
  pending: 'Ожидает',
  signed: 'Подписан',
  auto_signed: 'Авто-подписан',
}

export default function MyActsScreen() {
  const [acts, setActs] = useState<ActItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [signingId, setSigningId] = useState<number | null>(null)

  const fetchActs = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.get('acts/mine', { searchParams: { limit: 50 } }).json<{ items: ActItem[] }>()
      setActs(data.items)
    } catch {
      setError('Не удалось загрузить акты')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchActs() }, [])

  const handleSign = async (actId: number) => {
    setSigningId(actId)
    try {
      await api.post(`acts/${actId}/sign`).json()
      setActs((prev) => prev.map((a) => (a.id === actId ? { ...a, sign_status: 'signed' } : a)))
    } catch {
      setError('Ошибка при подписании акта')
    } finally {
      setSigningId(null)
    }
  }

  const handleDownload = async (actId: number) => {
    try {
      const response = await api.get(`acts/${actId}/pdf`, { timeout: 30_000 })
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `act_${actId}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      setError('Ошибка при скачивании PDF')
    }
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-20" />
        <Skeleton className="h-20" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-4">
        <Notification type="danger">{error}</Notification>
        <Button variant="secondary" fullWidth onClick={fetchActs}>Повторить</Button>
      </div>
    )
  }

  if (acts.length === 0) {
    return <EmptyState icon="📄" title="Актов пока нет" description="Акты появятся после завершения размещений" />
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-display font-bold text-text-primary">Мои акты</h1>

      <div className="space-y-3">
        {acts.map((act) => {
          const canSign = act.sign_status === 'draft' || act.sign_status === 'pending'
          return (
            <Card key={act.id} className="p-4">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <p className="text-sm font-semibold text-text-primary">
                    {TYPE_LABELS[act.act_type] ?? act.act_type} №{act.act_number}
                  </p>
                  <p className="text-xs text-text-tertiary">
                    от {new Date(act.act_date).toLocaleDateString('ru-RU')}
                  </p>
                </div>
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                  act.sign_status === 'signed' || act.sign_status === 'auto_signed'
                    ? 'bg-success-muted text-success'
                    : act.sign_status === 'pending'
                    ? 'bg-warning-muted text-warning'
                    : 'bg-harbor-elevated text-text-tertiary'
                }`}>
                  {STATUS_LABELS[act.sign_status] ?? act.sign_status}
                </span>
              </div>

              {(canSign || act.pdf_url) && (
                <div className="flex gap-2">
                  {canSign && (
                    <Button
                      variant="success"
                      size="sm"
                      loading={signingId === act.id}
                      onClick={() => handleSign(act.id)}
                    >
                      {signingId === act.id ? 'Подписание...' : 'Подписать'}
                    </Button>
                  )}
                  {act.pdf_url && (
                    <Button variant="secondary" size="sm" onClick={() => handleDownload(act.id)}>
                      📥 Скачать PDF
                    </Button>
                  )}
                </div>
              )}
            </Card>
          )
        })}
      </div>
    </div>
  )
}
