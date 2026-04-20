import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Notification,
  Button,
  Skeleton,
  Icon,
  ScreenHeader,
  Textarea,
  Timeline,
} from '@shared/ui'
import type { IconName } from '@shared/ui'
import { formatDateTimeMSK } from '@/lib/constants'
import { useDisputeById, useReplyToDispute } from '@/hooks/useDisputeQueries'

type Tone = 'danger' | 'warning' | 'success' | 'neutral'

const STATUS_META: Record<string, { label: string; tone: Tone; icon: IconName }> = {
  open: { label: 'Открыт', tone: 'danger', icon: 'warning' },
  owner_explained: { label: 'Ответ владельца', tone: 'warning', icon: 'hourglass' },
  resolved: { label: 'Решён', tone: 'success', icon: 'verified' },
  closed: { label: 'Закрыт', tone: 'neutral', icon: 'archive' },
}

const toneClasses: Record<Tone, string> = {
  danger: 'bg-danger-muted text-danger',
  warning: 'bg-warning-muted text-warning',
  success: 'bg-success-muted text-success',
  neutral: 'bg-harbor-elevated text-text-tertiary',
}

export default function DisputeDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const numId = id ? parseInt(id, 10) : null
  const { data: dispute, isLoading } = useDisputeById(numId)
  const replyMutation = useReplyToDispute()
  const [replyText, setReplyText] = useState('')

  if (isLoading) {
    return (
      <div className="max-w-[1080px] mx-auto space-y-4">
        <Skeleton className="h-20" />
        <Skeleton className="h-40" />
      </div>
    )
  }

  if (!dispute) {
    return (
      <div className="max-w-[1080px] mx-auto">
        <Notification type="danger">Спор не найден</Notification>
      </div>
    )
  }

  const meta = STATUS_META[dispute.status] ?? {
    label: dispute.status,
    tone: 'neutral' as Tone,
    icon: 'info' as IconName,
  }

  const timelineEvents = [
    {
      id: 'open',
      icon: '',
      title: 'Спор открыт',
      subtitle: formatDateTimeMSK(dispute.created_at),
      variant: 'danger' as const,
    },
    dispute.owner_explanation
      ? {
          id: 'owner',
          icon: '',
          title: 'Владелец дал объяснение',
          subtitle: 'Получено',
          variant: 'warning' as const,
        }
      : {
          id: 'owner',
          icon: '',
          title: 'Ожидание объяснения владельца',
          subtitle: 'Авто-решение, если объяснения нет 72 ч',
          variant: 'default' as const,
        },
    dispute.resolution
      ? {
          id: 'resolved',
          icon: '',
          title: 'Решение администратора',
          subtitle: dispute.resolution,
          variant: 'success' as const,
        }
      : {
          id: 'resolved',
          icon: '',
          title: 'Рассмотрение администратором',
          subtitle: 'До 48 часов после объяснения',
          variant: 'default' as const,
        },
  ]

  return (
    <div className="max-w-[1080px] mx-auto">
      <ScreenHeader
        crumbs={['Главная', 'Споры', `#${dispute.id}`]}
        title={`Спор #${dispute.id}`}
        subtitle={`Размещение #${dispute.placement_request_id}`}
        action={
          <Button variant="secondary" iconLeft="arrow-left" onClick={() => navigate('/disputes')}>
            К списку
          </Button>
        }
      />

      <div className="mb-5">
        <div
          className={`inline-flex items-center gap-2 text-[11px] font-bold tracking-[0.08em] uppercase py-1.5 px-2.5 rounded ${toneClasses[meta.tone]}`}
        >
          <Icon name={meta.icon} size={12} />
          {meta.label}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
        <div className="space-y-4">
          <div className="bg-harbor-card border border-border rounded-xl p-5">
            <div className="flex items-center gap-2 mb-3">
              <Icon name="flag" size={14} className="text-danger" />
              <span className="font-display text-[14px] font-semibold text-text-primary">
                Причина
              </span>
            </div>
            <p className="text-[13.5px] text-text-primary">{dispute.reason}</p>
          </div>

          <div className="bg-harbor-card border border-border rounded-xl p-5">
            <div className="flex items-center gap-2 mb-3">
              <Icon name="chat" size={14} className="text-text-tertiary" />
              <span className="font-display text-[14px] font-semibold text-text-primary">
                Комментарий рекламодателя
              </span>
            </div>
            <p className="text-[13.5px] leading-[1.55] text-text-secondary whitespace-pre-wrap">
              {dispute.advertiser_comment}
            </p>
          </div>

          {dispute.owner_explanation && (
            <div className="bg-harbor-card border border-border rounded-xl p-5">
              <div className="flex items-center gap-2 mb-3">
                <Icon name="chat" size={14} className="text-accent" />
                <span className="font-display text-[14px] font-semibold text-text-primary">
                  Объяснение владельца
                </span>
              </div>
              <p className="text-[13.5px] leading-[1.55] text-text-secondary whitespace-pre-wrap">
                {dispute.owner_explanation}
              </p>
            </div>
          )}

          {dispute.resolution && (
            <Notification type="success">
              <strong>Решение администратора:</strong> {dispute.resolution}
            </Notification>
          )}

          {dispute.status === 'open' && (
            <div className="bg-harbor-card border border-border rounded-xl p-5">
              <div className="flex items-center gap-2 mb-3">
                <Icon name="edit" size={14} className="text-accent" />
                <span className="font-display text-[14px] font-semibold text-text-primary">
                  Ваш ответ
                </span>
              </div>
              <Textarea
                rows={4}
                value={replyText}
                onChange={setReplyText}
                placeholder="Объясните вашу позицию…"
              />
              <Button
                variant="primary"
                iconLeft="check"
                className="mt-3"
                loading={replyMutation.isPending}
                disabled={!replyText.trim() || replyMutation.isPending}
                onClick={() =>
                  replyMutation.mutate(
                    { id: dispute.id, comment: replyText },
                    { onSuccess: () => setReplyText('') },
                  )
                }
              >
                Отправить ответ
              </Button>
            </div>
          )}
        </div>

        <div className="bg-harbor-card border border-border rounded-xl p-5 h-fit">
          <div className="font-display text-[14px] font-semibold text-text-primary mb-3">
            Хронология
          </div>
          <Timeline events={timelineEvents} />
        </div>
      </div>
    </div>
  )
}
