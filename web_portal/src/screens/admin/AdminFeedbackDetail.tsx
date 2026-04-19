import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, Button, Notification, Skeleton, Select, Textarea } from '@shared/ui'
import { formatDateTimeMSK } from '@/lib/constants'
import { useMe } from '@/hooks/queries'
import {
  useAdminFeedbackById,
  useRespondToFeedback,
  useUpdateFeedbackStatus,
} from '@/hooks/useFeedbackQueries'
import type { FeedbackStatusUpdatePayload } from '@/lib/types'

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
  const [responseStatus, setResponseStatus] = useState<'in_progress' | 'resolved' | 'rejected'>('resolved')
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
      <div className="space-y-4">
        <Skeleton className="h-20" />
        <Skeleton className="h-40" />
      </div>
    )
  }

  if (isError || !feedback) {
    return <Notification type="danger">{error ?? 'Обращение не найдено'}</Notification>
  }

  const statusColors: Record<string, string> = {
    new: 'text-warning',
    in_progress: 'text-info',
    resolved: 'text-success',
    rejected: 'text-danger',
  }

  const STATUS_LABELS: Record<string, string> = {
    new: 'Новое',
    in_progress: 'В работе',
    resolved: 'Решено',
    rejected: 'Отклонено',
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-display font-bold text-text-primary">Обращение #{feedback.id}</h1>
        <Button variant="secondary" size="sm" onClick={() => navigate('/admin/feedback')}>← Назад</Button>
      </div>

      <Card>
        <div className="space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="text-text-secondary">Пользователь</span>
            <span className="text-text-primary font-medium">
              {feedback.username ?? `User #${feedback.user_id}`}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-secondary">Статус</span>
            <span className={`font-semibold ${statusColors[feedback.status] ?? ''}`}>
              {feedback.status}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-secondary">Создано</span>
            <span className="text-text-primary">
              {formatDateTimeMSK(feedback.created_at)}
            </span>
          </div>
        </div>
      </Card>

      <Card title="Сообщение">
        <p className="text-text-primary whitespace-pre-wrap">{feedback.text}</p>
      </Card>

      {feedback.admin_response && (
        <Card title="Ответ администратора">
          <p className="text-text-secondary">{feedback.admin_response}</p>
          {feedback.responded_at && (
            <p className="text-xs text-text-tertiary mt-2">
              Ответ отправлен: {formatDateTimeMSK(feedback.responded_at)}
            </p>
          )}
        </Card>
      )}

      {!feedback.admin_response && (
        <Card title="Ответить">
          <div className="space-y-3">
            <Textarea
              rows={4}
              value={responseText}
              onChange={setResponseText}
              placeholder="Ваш ответ (мин. 10 символов)..."
            />
            <div className="flex gap-2">
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
                loading={respond.isPending}
                disabled={responseText.length < 10 || respond.isPending}
                onClick={handleRespond}
              >
                {respond.isPending ? 'Отправка...' : 'Отправить'}
              </Button>
            </div>
          </div>
        </Card>
      )}

      <Card title="Сменить статус">
        <div className="flex gap-2 flex-wrap">
          {(['new', 'in_progress', 'resolved', 'rejected'] as const).map((status) => (
            <Button
              key={status}
              variant={feedback.status === status ? 'primary' : 'secondary'}
              size="sm"
              onClick={() => handleStatusChange(status)}
            >
              {STATUS_LABELS[status] ?? status}
            </Button>
          ))}
        </div>
      </Card>
    </div>
  )
}
