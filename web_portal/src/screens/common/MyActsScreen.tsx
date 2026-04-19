import { useState } from 'react'
import { Card, Button, Skeleton, EmptyState, Notification } from '@shared/ui'
import { formatDateMSK } from '@/lib/constants'
import { useMyActs, useSignAct, downloadActPdf } from '@/hooks/useActQueries'

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
  const { data, isLoading, isError, refetch } = useMyActs({ limit: 50 })
  const signMutation = useSignAct()
  const [error, setError] = useState<string | null>(null)
  const [downloadingId, setDownloadingId] = useState<number | null>(null)

  const acts = data?.items ?? []

  const handleSign = (actId: number) => {
    signMutation.mutate(actId, {
      onError: () => setError('Ошибка при подписании акта'),
    })
  }

  const handleDownload = async (actId: number) => {
    setDownloadingId(actId)
    try {
      await downloadActPdf(actId)
    } catch {
      setError('Ошибка при скачивании PDF')
    } finally {
      setDownloadingId(null)
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-20" />
        <Skeleton className="h-20" />
      </div>
    )
  }

  if (isError) {
    return (
      <div className="space-y-4">
        <Notification type="danger">{error ?? 'Не удалось загрузить акты'}</Notification>
        <Button variant="secondary" fullWidth onClick={() => refetch()}>Повторить</Button>
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
                    от {formatDateMSK(act.act_date)}
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
                      loading={signMutation.isPending && signMutation.variables === act.id}
                      onClick={() => handleSign(act.id)}
                    >
                      {signMutation.isPending && signMutation.variables === act.id ? 'Подписание...' : 'Подписать'}
                    </Button>
                  )}
                  {act.pdf_url && (
                    <Button
                      variant="secondary"
                      size="sm"
                      loading={downloadingId === act.id}
                      onClick={() => handleDownload(act.id)}
                    >
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
