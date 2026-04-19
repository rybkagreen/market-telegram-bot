import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, Button, Notification, Skeleton } from '@shared/ui'
import { PUBLICATION_FORMATS, formatCurrency, formatDateTimeMSK } from '@/lib/constants'
import { usePlacement } from '@/hooks/useCampaignQueries'
import { useCreateDispute, useDisputeEvidence } from '@/hooks/useDisputeQueries'

const MIN_DISPUTE_COMMENT = 20

const DISPUTE_REASONS = [
  { key: 'post_removed_early', icon: '🗑', label: 'Пост удалён досрочно' },
  { key: 'bot_kicked', icon: '🤖', label: 'Бот удалён из канала' },
  { key: 'advertiser_complaint', icon: '💬', label: 'Жалоба рекламодателя' },
]

function formatDateTime(dt: string | null | undefined): string {
  return formatDateTimeMSK(dt)
}

export default function OpenDispute() {
  const { id } = useParams()
  const navigate = useNavigate()

  const numId = id ? parseInt(id, 10) : null
  const { data: placement, isLoading } = usePlacement(numId)
  const { data: evidence } = useDisputeEvidence(numId)
  const { mutate: createDispute, isPending: submitting, isError: submitError } = useCreateDispute()

  const [selectedReason, setSelectedReason] = useState<string | null>(null)
  const [comment, setComment] = useState('')
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    const interval = setInterval(() => setNow(Date.now()), 60000)
    return () => clearInterval(interval)
  }, [])

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-32" />
        <Skeleton className="h-40" />
      </div>
    )
  }

  if (!placement) {
    return <Notification type="danger">Заявка не найдена</Notification>
  }

  const isInWindow = placement.published_at
    ? now - new Date(placement.published_at).getTime() <= 48 * 60 * 60 * 1000
    : false

  const isPublished = placement.status === 'published'
  const canOpen = isPublished && !placement.has_dispute && isInWindow

  if (!canOpen) {
    const reason = !isPublished
      ? 'Спор можно открыть только для опубликованных кампаний'
      : placement.has_dispute
        ? 'Спор уже открыт для этой кампании'
        : 'Время для открытия спора истекло (48ч)'

    return (
      <div className="space-y-4">
        <Notification type="danger">❌ {reason}</Notification>
        <Button variant="secondary" fullWidth onClick={() => navigate(-1 as unknown as string)}>
          Назад
        </Button>
      </div>
    )
  }

  const handleOpen = () => {
    if (!selectedReason || comment.length < MIN_DISPUTE_COMMENT || !placement) return
    createDispute(
      { placement_id: placement.id, reason: selectedReason, comment },
      { onSuccess: () => navigate(`/adv/campaigns/${placement.id}/published`) },
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-display font-bold text-text-primary">Открыть спор</h1>

      <Card title="Кампания">
        <div className="space-y-2 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-text-secondary">Канал</span>
            <span className="text-text-primary font-medium">
              @{placement.channel?.username ?? `#${placement.channel_id}`}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-text-secondary">Формат</span>
            <span className="text-text-primary">
              {PUBLICATION_FORMATS[placement.publication_format]?.icon}{' '}
              {PUBLICATION_FORMATS[placement.publication_format]?.name ?? placement.publication_format}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-text-secondary">Цена</span>
            <span className="text-text-primary font-semibold">
              {formatCurrency(placement.final_price ?? placement.counter_price ?? placement.proposed_price)}
            </span>
          </div>
          {placement.published_at && (
            <div className="flex items-center justify-between">
              <span className="text-text-secondary">Опубликовано</span>
              <span className="text-text-primary">{formatDateTime(placement.published_at)}</span>
            </div>
          )}
        </div>
      </Card>

      {evidence && (
        <Card title="Что мы знаем о публикации">
          <div className="space-y-2 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-text-secondary">Опубликовано</span>
              <span className="text-text-primary">
                {evidence.summary.published_at
                  ? formatDateTime(evidence.summary.published_at)
                  : '—'}
              </span>
            </div>
            {evidence.summary.deleted_at && (
              <div className="flex items-center justify-between">
                <span className="text-text-secondary">
                  Удалено{' '}
                  {evidence.summary.deletion_type === 'early_by_owner'
                    ? '(досрочно владельцем)'
                    : '(ботом)'}
                </span>
                <span className="text-text-primary">{formatDateTime(evidence.summary.deleted_at)}</span>
              </div>
            )}
            <div className="flex items-center justify-between">
              <span className="text-text-secondary">Длительность поста</span>
              <span className="text-text-primary">
                {evidence.summary.total_duration_minutes} мин
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-text-secondary">ERID</span>
              <span className="text-text-primary">
                {evidence.summary.erid_present ? '✅ присутствует' : '❌ отсутствует'}
              </span>
            </div>
            {evidence.events.length > 0 && (
              <details className="pt-2 border-t border-border">
                <summary className="cursor-pointer text-text-secondary text-xs">
                  Лог событий ({evidence.events.length})
                </summary>
                <ul className="mt-2 space-y-1 text-xs text-text-tertiary">
                  {evidence.events.map((ev) => (
                    <li key={ev.id} className="flex items-start gap-2">
                      <span className="font-mono">{formatDateTime(ev.detected_at)}</span>
                      <span className="flex-1">{ev.event_type}</span>
                      {ev.post_url && (
                        <a
                          href={ev.post_url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-accent hover:underline"
                        >
                          пост
                        </a>
                      )}
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </div>
        </Card>
      )}

      {/* Reason selection */}
      <div>
        <p className="text-sm font-medium text-text-secondary mb-2">Причина спора</p>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {DISPUTE_REASONS.map(({ key, icon, label }) => (
            <button
              key={key}
              className={`flex flex-col items-center gap-1 p-3 rounded-lg border transition-all ${
                selectedReason === key
                  ? 'border-danger bg-danger-muted text-danger'
                  : 'border-border bg-harbor-card text-text-secondary hover:border-danger/50'
              }`}
              onClick={() => setSelectedReason(key)}
            >
              <span className="text-xl">{icon}</span>
              <span className="text-xs font-medium text-center">{label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Comment */}
      <div>
        <label className="block text-sm font-medium text-text-secondary mb-1">
          Опишите проблему подробно
        </label>
        <textarea
          className="w-full px-4 py-2.5 bg-harbor-elevated border border-border rounded-md text-sm text-text-primary placeholder:text-text-tertiary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/30 resize-none"
          rows={4}
          placeholder={`Минимум ${MIN_DISPUTE_COMMENT} символов. Подробное описание поможет быстрее разрешить спор.`}
          value={comment}
          onChange={(e) => setComment(e.target.value)}
        />
        <p className="text-xs text-text-tertiary mt-1">
          {comment.length} / мин. {MIN_DISPUTE_COMMENT}
        </p>
      </div>

      <Notification type="warning">
        <span className="text-sm">⚠️ Необоснованные споры могут повлиять на вашу репутацию</span>
      </Notification>

      {submitError && <Notification type="danger">Не удалось открыть спор. Попробуйте снова.</Notification>}

      <Button
        variant="danger"
        fullWidth
        loading={submitting}
        disabled={!selectedReason || comment.length < MIN_DISPUTE_COMMENT || submitting}
        onClick={handleOpen}
      >
        ⚠️ Открыть спор
      </Button>
    </div>
  )
}
