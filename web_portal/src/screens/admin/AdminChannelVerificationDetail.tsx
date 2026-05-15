import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Button,
  Notification,
  Skeleton,
  Textarea,
  Icon,
  ScreenHeader,
} from '@shared/ui'
import { formatDateTimeMSK } from '@/lib/constants'
import {
  useAdminChannelVerificationDetail,
  useVerifyChannelManually,
  useRejectChannelVerification,
} from '@/hooks/useChannelVerificationQueries'

type Mode = null | 'verify' | 'reject'

const HISTORY_LABELS: Record<string, string> = {
  blogger_registry_evidence_submitted: 'Подана заявка',
  blogger_registry_verified_by_admin: 'Подтверждено администратором',
  blogger_registry_rejected_by_admin: 'Отклонено администратором',
}

export default function AdminChannelVerificationDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const channelId = id ? Number(id) : null

  const { data, isLoading, isError } = useAdminChannelVerificationDetail(channelId)
  const verifyMutation = useVerifyChannelManually()
  const rejectMutation = useRejectChannelVerification()

  const [mode, setMode] = useState<Mode>(null)
  const [verifyNotes, setVerifyNotes] = useState('')
  const [rejectReason, setRejectReason] = useState('')
  const [rejectInternal, setRejectInternal] = useState('')
  const [actionError, setActionError] = useState<string | null>(null)

  const closeMode = () => {
    setMode(null)
    setVerifyNotes('')
    setRejectReason('')
    setRejectInternal('')
    setActionError(null)
  }

  const handleVerify = () => {
    if (!channelId) return
    setActionError(null)
    verifyMutation.mutate(
      { channelId, body: { notes: verifyNotes || null } },
      {
        onSuccess: () => {
          closeMode()
          navigate('/admin/channel-verifications')
        },
        onError: () => setActionError('Ошибка при подтверждении канала'),
      },
    )
  }

  const handleReject = () => {
    if (!channelId) return
    if (!rejectReason.trim()) {
      setActionError('Укажите причину отказа')
      return
    }
    setActionError(null)
    rejectMutation.mutate(
      {
        channelId,
        body: {
          reason: rejectReason,
          internal_notes: rejectInternal || null,
        },
      },
      {
        onSuccess: () => {
          closeMode()
          navigate('/admin/channel-verifications')
        },
        onError: () => setActionError('Ошибка при отклонении заявки'),
      },
    )
  }

  if (isLoading) {
    return (
      <div className="max-w-[1080px] mx-auto space-y-4">
        <Skeleton className="h-20" />
        <Skeleton className="h-64" />
      </div>
    )
  }

  if (isError || !data) {
    return (
      <div className="max-w-[1080px] mx-auto">
        <Notification type="danger">Канал или заявка не найдены</Notification>
      </div>
    )
  }

  const isVerified = data.is_blogger_registry_verified
  const submitted = data.application_number != null
  const canVerify = submitted && !isVerified
  const canReject = submitted

  return (
    <div className="max-w-[1080px] mx-auto">
      <ScreenHeader
        title={`Заявка на верификацию #${data.channel_id}`}
        subtitle={
          isVerified
            ? `Канал подтверждён (${data.blogger_registry_verification_method ?? '—'})`
            : 'Ручная проверка реестра блогеров (ФЗ-303)'
        }
        action={
          <Button
            variant="secondary"
            size="sm"
            iconLeft="arrow-left"
            onClick={() => navigate('/admin/channel-verifications')}
          >
            К списку
          </Button>
        }
      />

      {/* Channel info */}
      <div className="grid gap-4 lg:grid-cols-2 mb-4">
        <div className="bg-harbor-card border border-border rounded-xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <Icon name="channels" size={14} className="text-text-tertiary" />
            <span className="font-display text-[14px] font-semibold text-text-primary">
              Канал
            </span>
          </div>
          <div className="space-y-2 text-[13px]">
            <DetailRow label="Название">
              <span className="text-text-primary">{data.channel_title ?? '—'}</span>
            </DetailRow>
            <DetailRow label="Username">
              <span className="font-mono text-text-primary">
                {data.channel_username ? `@${data.channel_username}` : '—'}
              </span>
            </DetailRow>
            <DetailRow label="Подписчиков">
              <span className="font-mono tabular-nums text-text-primary">
                {data.member_count.toLocaleString('ru-RU')}
              </span>
            </DetailRow>
            {data.member_count_at_verification != null && (
              <DetailRow label="Подписчиков на момент верификации">
                <span className="font-mono tabular-nums text-text-secondary">
                  {data.member_count_at_verification.toLocaleString('ru-RU')}
                </span>
              </DetailRow>
            )}
            <DetailRow label="Владелец">
              <span className="text-text-primary">
                #{data.owner_id}
                {data.owner_username ? ` (@${data.owner_username})` : ''}
              </span>
            </DetailRow>
          </div>
        </div>

        <div className="bg-harbor-card border border-border rounded-xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <Icon name="verified" size={14} className="text-text-tertiary" />
            <span className="font-display text-[14px] font-semibold text-text-primary">
              Статус регистрации
            </span>
          </div>
          <div className="space-y-2 text-[13px]">
            <DetailRow label="Верифицирован">
              <span className={isVerified ? 'text-success font-semibold' : 'text-warning font-semibold'}>
                {isVerified ? 'Да' : 'Нет'}
              </span>
            </DetailRow>
            <DetailRow label="Номер заявления">
              <span className="font-mono text-text-primary">
                {data.application_number ?? '—'}
              </span>
            </DetailRow>
            {data.blogger_registry_verified_at && (
              <DetailRow label="Подтверждено">
                <span className="text-text-secondary tabular-nums">
                  {formatDateTimeMSK(data.blogger_registry_verified_at)} МСК
                </span>
              </DetailRow>
            )}
            {data.blogger_registry_verification_method && (
              <DetailRow label="Метод">
                <span className="text-text-secondary">
                  {data.blogger_registry_verification_method}
                </span>
              </DetailRow>
            )}
            {data.blogger_registry_verified_by_admin_id != null && (
              <DetailRow label="Подтвердил админ">
                <span className="text-text-secondary">
                  #{data.blogger_registry_verified_by_admin_id}
                </span>
              </DetailRow>
            )}
            {data.last_blogger_registry_check_at && (
              <DetailRow label="Последняя проверка">
                <span className="text-text-secondary tabular-nums">
                  {formatDateTimeMSK(data.last_blogger_registry_check_at)} МСК
                </span>
              </DetailRow>
            )}
          </div>
        </div>
      </div>

      {/* History */}
      <div className="bg-harbor-card border border-border rounded-xl p-5 mb-4">
        <div className="flex items-center gap-2 mb-3">
          <Icon name="clock" size={14} className="text-text-tertiary" />
          <span className="font-display text-[14px] font-semibold text-text-primary">
            История
          </span>
        </div>
        {data.history.length === 0 ? (
          <p className="text-[12.5px] text-text-tertiary italic">
            Нет записей в журнале по этому каналу.
          </p>
        ) : (
          <ul className="space-y-2.5">
            {data.history.map((entry, idx) => (
              <li
                key={`${entry.action}-${entry.created_at}-${idx}`}
                className="flex items-start gap-3 text-[12.5px]"
              >
                <span className="grid place-items-center w-6 h-6 rounded bg-harbor-elevated text-text-tertiary flex-shrink-0">
                  <Icon name="info" size={11} />
                </span>
                <div className="flex-1">
                  <div className="text-text-primary font-semibold">
                    {HISTORY_LABELS[entry.action] ?? entry.action}
                  </div>
                  <div className="text-text-tertiary tabular-nums">
                    {formatDateTimeMSK(entry.created_at)} МСК
                    {entry.actor_user_id != null && ` · пользователь #${entry.actor_user_id}`}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Actions / Inline forms */}
      {actionError && (
        <div className="mb-4">
          <Notification type="danger">{actionError}</Notification>
        </div>
      )}

      {!mode && (canVerify || canReject) && (
        <div className="flex gap-3 flex-wrap">
          {canVerify && (
            <Button variant="primary" iconLeft="check" onClick={() => setMode('verify')}>
              Подтвердить
            </Button>
          )}
          {canReject && (
            <Button variant="danger" iconLeft="error" onClick={() => setMode('reject')}>
              Отклонить
            </Button>
          )}
        </div>
      )}

      {mode === 'verify' && (
        <div className="bg-harbor-card border border-success/25 rounded-xl p-5">
          <div className="font-display text-[14px] font-semibold text-text-primary mb-3">
            Подтвердить канал
          </div>
          <Textarea
            value={verifyNotes}
            onChange={setVerifyNotes}
            placeholder="Внутренние заметки (опционально, до 1000 символов)"
            rows={3}
          />
          <div className="flex gap-2 mt-3">
            <Button
              variant="primary"
              iconLeft="check"
              onClick={handleVerify}
              disabled={verifyMutation.isPending}
            >
              {verifyMutation.isPending ? 'Подтверждение…' : 'Подтвердить'}
            </Button>
            <Button variant="ghost" onClick={closeMode}>
              Отмена
            </Button>
          </div>
        </div>
      )}

      {mode === 'reject' && (
        <div className="bg-harbor-card border border-danger/25 rounded-xl p-5 space-y-3">
          <div className="font-display text-[14px] font-semibold text-text-primary">
            Отклонить заявку
          </div>
          <Textarea
            value={rejectReason}
            onChange={setRejectReason}
            placeholder="Причина отказа (видна владельцу, обязательно, до 1000 символов)"
            rows={3}
          />
          <Textarea
            value={rejectInternal}
            onChange={setRejectInternal}
            placeholder="Внутренние заметки (не отправляются владельцу, опционально)"
            rows={2}
          />
          <div className="flex gap-2">
            <Button
              variant="danger"
              iconLeft="error"
              onClick={handleReject}
              disabled={rejectMutation.isPending}
            >
              {rejectMutation.isPending ? 'Отклонение…' : 'Отклонить'}
            </Button>
            <Button variant="ghost" onClick={closeMode}>
              Отмена
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

function DetailRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <span className="text-text-tertiary text-[12px]">{label}</span>
      <span className="text-right">{children}</span>
    </div>
  )
}
