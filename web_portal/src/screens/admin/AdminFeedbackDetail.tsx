import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Button,
  Notification,
  Skeleton,
  Select,
  Textarea,
  Icon,
  ScreenHeader,
} from '@shared/ui'
import type { IconName } from '@shared/ui'
import { formatDateTimeMSK } from '@/lib/constants'
import { useMe } from '@/hooks/queries'
import {
  useAdminFeedbackById,
  useRespondToFeedback,
  useUpdateFeedbackStatus,
} from '@/hooks/useFeedbackQueries'
import type { FeedbackStatusUpdatePayload } from '@/lib/types'

type Tone = 'info' | 'warning' | 'success' | 'danger' | 'neutral'

const STATUS_META: Record<string, { label: string; tone: Tone; icon: IconName }> = {
  new: { label: 'Новое', tone: 'info', icon: 'pending' },
  in_progress: { label: 'В работе', tone: 'warning', icon: 'hourglass' },
  resolved: { label: 'Решено', tone: 'success', icon: 'verified' },
  rejected: { label: 'Отклонено', tone: 'danger', icon: 'close' },
}

const toneClasses: Record<Tone, string> = {
  info: 'bg-info-muted text-info',
  warning: 'bg-warning-muted text-warning',
  success: 'bg-success-muted text-success',
  danger: 'bg-danger-muted text-danger',
  neutral: 'bg-harbor-elevated text-text-tertiary',
}

export default function AdminFeedbackDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: user } = useMe()
  const feedbackId = Number(id)

  const {
    data: feedback,
    isLoading: loading,
    isError,
  } = useAdminFeedbackById(user?.is_admin ? feedbackId : 0)
  const respond = useRespondToFeedback()
  const updateStatus = useUpdateFeedbackStatus()

  const [responseText, setResponseText] = useState('')
  const [responseStatus, setResponseStatus] =
    useState<'in_progress' | 'resolved' | 'rejected'>('resolved')
  const [error, setError] = useState<string | null>(null)

  const handleRespond = () => {
    if (!feedbackId || responseText.length < 10) return
    respond.mutate(
      { feedbackId, payload: { response_text: responseText, status: responseStatus } },
      {
        onSuccess: () => {
          setResponseText('')
          navigate('/admin/feedback')
        },
        onError: () => setError('Ошибка при отправке'),
      },
    )
  }

  const handleStatusChange = (status: FeedbackStatusUpdatePayload['status']) => {
    if (!feedbackId) return
    updateStatus.mutate(
      { feedbackId, payload: { status } },
      { onError: () => setError('Ошибка при смене статуса') },
    )
  }

  if (loading) {
    return (
      <div className="max-w-[1080px] mx-auto space-y-4">
        <Skeleton className="h-20" />
        <Skeleton className="h-40" />
      </div>
    )
  }

  if (isError || !feedback) {
    return (
      <div className="max-w-[1080px] mx-auto">
        <Notification type="danger">{error ?? 'Обращение не найдено'}</Notification>
      </div>
    )
  }

  const status = STATUS_META[feedback.status] ?? {
    label: feedback.status,
    tone: 'neutral' as Tone,
    icon: 'info' as IconName,
  }

  return (
    <div className="max-w-[1080px] mx-auto">
      <ScreenHeader
        title={`Обращение #${feedback.id}`}
        subtitle={feedback.username ? `От @${feedback.username}` : `От User #${feedback.user_id}`}
        action={
          <Button
            variant="secondary"
            size="sm"
            iconLeft="arrow-left"
            onClick={() => navigate('/admin/feedback')}
          >
            К списку
          </Button>
        }
      />

      <div className="mb-5 flex items-center gap-3 flex-wrap">
        <span
          className={`inline-flex items-center gap-1.5 text-[10.5px] font-bold tracking-[0.08em] uppercase py-1 px-2 rounded ${toneClasses[status.tone]}`}
        >
          <Icon name={status.icon} size={12} />
          {status.label}
        </span>
        <span className="text-[12px] text-text-tertiary tabular-nums">
          Создано {formatDateTimeMSK(feedback.created_at)} МСК
        </span>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
        <div className="space-y-4">
          <div className="bg-harbor-card border border-border rounded-xl p-5">
            <div className="flex items-center gap-2 mb-3">
              <Icon name="chat" size={14} className="text-text-tertiary" />
              <span className="font-display text-[14px] font-semibold text-text-primary">
                Сообщение пользователя
              </span>
            </div>
            <p className="text-[13.5px] leading-[1.55] text-text-secondary whitespace-pre-wrap">
              {feedback.text}
            </p>
          </div>

          {feedback.admin_response && (
            <div className="bg-harbor-card border border-success/25 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-3">
                <Icon name="verified" size={14} className="text-success" variant="fill" />
                <span className="font-display text-[14px] font-semibold text-text-primary">
                  Ответ администратора
                </span>
              </div>
              <p className="text-[13.5px] leading-[1.55] text-text-secondary whitespace-pre-wrap">
                {feedback.admin_response}
              </p>
              {feedback.responded_at && (
                <p className="text-[11.5px] text-text-tertiary mt-2 tabular-nums">
                  Отправлено: {formatDateTimeMSK(feedback.responded_at)}
                </p>
              )}
            </div>
          )}

          {!feedback.admin_response && (
            <div className="bg-harbor-card border border-border rounded-xl p-5">
              <div className="flex items-center gap-2 mb-3">
                <Icon name="edit" size={14} className="text-accent" />
                <span className="font-display text-[14px] font-semibold text-text-primary">
                  Ответить
                </span>
              </div>
              <Textarea
                rows={4}
                value={responseText}
                onChange={setResponseText}
                placeholder="Ваш ответ (мин. 10 символов)…"
              />
              <div className="mt-3 flex gap-2 flex-wrap items-center">
                <Select
                  value={responseStatus}
                  onChange={(v) => setResponseStatus(v as typeof responseStatus)}
                  options={[
                    { value: 'resolved', label: 'Решено' },
                    { value: 'in_progress', label: 'В работе' },
                    { value: 'rejected', label: 'Отклонено' },
                  ]}
                />
                <Button
                  variant="primary"
                  iconLeft="check"
                  loading={respond.isPending}
                  disabled={responseText.length < 10 || respond.isPending}
                  onClick={handleRespond}
                >
                  Отправить
                </Button>
              </div>
            </div>
          )}
        </div>

        <div className="bg-harbor-card border border-border rounded-xl p-5 h-fit">
          <div className="font-display text-[14px] font-semibold text-text-primary mb-3">
            Сменить статус
          </div>
          <div className="flex flex-col gap-2">
            {(['new', 'in_progress', 'resolved', 'rejected'] as const).map((s) => {
              const meta = STATUS_META[s]
              const on = feedback.status === s
              return (
                <Button
                  key={s}
                  variant={on ? 'primary' : 'secondary'}
                  size="sm"
                  fullWidth
                  iconLeft={meta.icon}
                  onClick={() => handleStatusChange(s)}
                >
                  {meta.label}
                </Button>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
