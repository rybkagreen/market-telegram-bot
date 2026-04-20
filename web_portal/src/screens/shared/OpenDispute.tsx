import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Button,
  Notification,
  Skeleton,
  Icon,
  ScreenHeader,
  Textarea,
} from '@shared/ui'
import type { IconName } from '@shared/ui'
import { PUBLICATION_FORMATS, formatCurrency, formatDateTimeMSK } from '@/lib/constants'
import { usePlacement } from '@/hooks/useCampaignQueries'
import { useCreateDispute, useDisputeEvidence } from '@/hooks/useDisputeQueries'

const MIN_DISPUTE_COMMENT = 20

const DISPUTE_REASONS: { key: string; icon: IconName; label: string }[] = [
  { key: 'post_removed_early', icon: 'delete', label: 'Пост удалён досрочно' },
  { key: 'bot_kicked', icon: 'blocked', label: 'Бот удалён из канала' },
  { key: 'advertiser_complaint', icon: 'chat', label: 'Жалоба рекламодателя' },
]

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
      <div className="max-w-[1080px] mx-auto space-y-4">
        <Skeleton className="h-20" />
        <Skeleton className="h-40" />
      </div>
    )
  }

  if (!placement) {
    return (
      <div className="max-w-[1080px] mx-auto">
        <Notification type="danger">Заявка не найдена</Notification>
      </div>
    )
  }

  const isInWindow = placement.published_at
    ? now - new Date(placement.published_at).getTime() <= 48 * 60 * 60 * 1000
    : false
  const isPublished = placement.status === 'published'
  const canOpen = isPublished && !placement.has_dispute && isInWindow

  if (!canOpen) {
    const reason = !isPublished
      ? 'Спор можно открыть только для опубликованных кампаний.'
      : placement.has_dispute
        ? 'Спор уже открыт для этой кампании.'
        : 'Время для открытия спора истекло (48 ч).'
    return (
      <div className="max-w-[1080px] mx-auto space-y-4">
        <ScreenHeader
          crumbs={['Главная', 'Споры', 'Открыть спор']}
          title="Открыть спор"
        />
        <Notification type="danger">{reason}</Notification>
        <Button variant="secondary" iconLeft="arrow-left" onClick={() => navigate(-1 as unknown as string)}>
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

  const fmt = PUBLICATION_FORMATS[placement.publication_format]

  return (
    <div className="max-w-[1080px] mx-auto">
      <ScreenHeader
        crumbs={['Главная', 'Споры', 'Открыть спор']}
        title="Открыть спор"
        subtitle="Укажите причину и опишите, что пошло не так. Приложим автоматический лог публикации."
        action={
          <Button
            variant="secondary"
            iconLeft="arrow-left"
            onClick={() => navigate(-1 as unknown as string)}
          >
            Назад
          </Button>
        }
      />

      <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
        <div className="space-y-4">
          <div className="bg-harbor-card border border-border rounded-xl p-5">
            <div className="flex items-center gap-2 mb-3">
              <Icon name="warning" size={14} className="text-danger" />
              <span className="font-display text-[14px] font-semibold text-text-primary">
                Причина спора
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              {DISPUTE_REASONS.map(({ key, icon, label }) => {
                const on = selectedReason === key
                return (
                  <button
                    key={key}
                    type="button"
                    className={`flex flex-col items-center gap-2 p-3.5 rounded-lg border transition-all ${
                      on
                        ? 'border-danger bg-danger-muted text-danger'
                        : 'border-border bg-harbor-secondary text-text-secondary hover:border-danger/40'
                    }`}
                    onClick={() => setSelectedReason(key)}
                  >
                    <Icon name={icon} size={18} />
                    <span className="text-xs font-semibold text-center">{label}</span>
                  </button>
                )
              })}
            </div>
          </div>

          <div className="bg-harbor-card border border-border rounded-xl p-5">
            <div className="flex items-center gap-2 mb-3">
              <Icon name="edit" size={14} className="text-text-tertiary" />
              <span className="font-display text-[14px] font-semibold text-text-primary">
                Описание проблемы
              </span>
            </div>
            <Textarea
              rows={5}
              value={comment}
              onChange={setComment}
              placeholder={`Минимум ${MIN_DISPUTE_COMMENT} символов. Хронология, скриншоты в комментарии, ссылки.`}
            />
            <p
              className={`text-[11.5px] mt-1.5 flex items-center gap-1.5 ${comment.length >= MIN_DISPUTE_COMMENT ? 'text-success' : 'text-text-tertiary'}`}
            >
              <Icon
                name={comment.length >= MIN_DISPUTE_COMMENT ? 'check' : 'hourglass'}
                size={12}
              />
              {comment.length} / мин. {MIN_DISPUTE_COMMENT} символов
            </p>
          </div>

          <Notification type="warning">
            Необоснованные споры могут повлиять на вашу репутацию. Укажите только реальные нарушения.
          </Notification>

          {submitError && (
            <Notification type="danger">Не удалось открыть спор. Попробуйте снова.</Notification>
          )}

          <Button
            variant="danger"
            iconLeft="warning"
            fullWidth
            loading={submitting}
            disabled={!selectedReason || comment.length < MIN_DISPUTE_COMMENT || submitting}
            onClick={handleOpen}
          >
            Открыть спор
          </Button>
        </div>

        <div className="space-y-4">
          <div className="bg-harbor-card border border-border rounded-xl p-5 h-fit">
            <div className="font-display text-[14px] font-semibold text-text-primary mb-3">
              Кампания
            </div>
            <dl className="space-y-2.5 text-[13px]">
              <DetailRow icon="channels" label="Канал">
                @{placement.channel?.username ?? `#${placement.channel_id}`}
              </DetailRow>
              <DetailRow icon="docs" label="Формат">
                {fmt?.name ?? placement.publication_format}
              </DetailRow>
              <DetailRow icon="ruble" label="Цена">
                <span className="font-mono tabular-nums font-semibold text-text-primary">
                  {formatCurrency(
                    placement.final_price ?? placement.counter_price ?? placement.proposed_price,
                  )}
                </span>
              </DetailRow>
              {placement.published_at && (
                <DetailRow icon="calendar" label="Опубликовано">
                  <span className="tabular-nums">{formatDateTimeMSK(placement.published_at)}</span>
                </DetailRow>
              )}
            </dl>
          </div>

          {evidence && (
            <div className="bg-harbor-card border border-border rounded-xl p-5 h-fit">
              <div className="font-display text-[14px] font-semibold text-text-primary mb-3">
                Факты о публикации
              </div>
              <dl className="space-y-2.5 text-[13px]">
                <DetailRow icon="calendar" label="Опубликовано">
                  {evidence.summary.published_at
                    ? formatDateTimeMSK(evidence.summary.published_at)
                    : '—'}
                </DetailRow>
                {evidence.summary.deleted_at && (
                  <DetailRow icon="delete" label="Удалено">
                    <span className="text-text-primary">
                      {formatDateTimeMSK(evidence.summary.deleted_at)}
                      <span className="block text-[11px] text-text-tertiary">
                        {evidence.summary.deletion_type === 'early_by_owner'
                          ? 'досрочно владельцем'
                          : 'ботом'}
                      </span>
                    </span>
                  </DetailRow>
                )}
                <DetailRow icon="clock" label="Длительность">
                  <span className="font-mono tabular-nums">
                    {evidence.summary.total_duration_minutes} мин
                  </span>
                </DetailRow>
                <DetailRow icon="verified" label="ERID">
                  <span
                    className={`text-[10.5px] font-bold tracking-[0.08em] uppercase py-0.5 px-1.5 rounded ${evidence.summary.erid_present ? 'bg-success-muted text-success' : 'bg-warning-muted text-warning'}`}
                  >
                    {evidence.summary.erid_present ? 'Есть' : 'Нет'}
                  </span>
                </DetailRow>
              </dl>
              {evidence.events.length > 0 && (
                <details className="mt-3 pt-3 border-t border-border">
                  <summary className="cursor-pointer text-[12px] text-text-secondary flex items-center gap-1.5">
                    <Icon name="audit" size={12} />
                    Лог событий ({evidence.events.length})
                  </summary>
                  <ul className="mt-2 space-y-1 text-[11.5px] text-text-tertiary">
                    {evidence.events.map((ev) => (
                      <li key={ev.id} className="flex items-start gap-2">
                        <span className="font-mono tabular-nums">
                          {formatDateTimeMSK(ev.detected_at)}
                        </span>
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
          )}
        </div>
      </div>
    </div>
  )
}

function DetailRow({
  icon,
  label,
  children,
}: {
  icon: 'channels' | 'docs' | 'ruble' | 'calendar' | 'delete' | 'clock' | 'verified'
  label: string
  children: React.ReactNode
}) {
  return (
    <div className="flex items-start justify-between gap-3">
      <span className="flex items-center gap-2 text-text-secondary">
        <Icon name={icon} size={13} className="text-text-tertiary" />
        {label}
      </span>
      <span className="text-text-primary text-right">{children}</span>
    </div>
  )
}
