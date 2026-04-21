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
import type { IconName } from '@shared/ui'
import { formatDateTimeMSK } from '@/lib/constants'
import { useDisputeById, useResolveDispute } from '@/hooks/useDisputeQueries'
import { getDisputeStatusMeta, DISPUTE_TONE_CLASSES } from '@/lib/disputeLabels'

type Resolution = 'owner_fault' | 'advertiser_fault' | 'technical' | 'partial'

const RESOLUTION_META: Record<
  Resolution,
  { label: string; description: string; icon: IconName; tone: 'danger' | 'warning' | 'accent' | 'accent2' }
> = {
  owner_fault: {
    label: 'Виноват владелец',
    description: 'Полный возврат рекламодателю (100%), владельцу 0%.',
    icon: 'warning',
    tone: 'danger',
  },
  advertiser_fault: {
    label: 'Виноват рекламодатель',
    description: 'Без возврата рекламодателю (0%), владельцу 100%.',
    icon: 'check',
    tone: 'accent',
  },
  technical: {
    label: 'Технический сбой',
    description: 'Полный возврат рекламодателю (100%), платформа покрывает убыток.',
    icon: 'zap',
    tone: 'warning',
  },
  partial: {
    label: 'Частично',
    description: 'Возврат разделяется согласно бегунку ниже.',
    icon: 'percent',
    tone: 'accent2',
  },
}

const resolutionToneClasses: Record<
  'danger' | 'warning' | 'accent' | 'accent2',
  { on: string; off: string }
> = {
  danger: {
    on: 'border-danger bg-danger-muted text-danger',
    off: 'border-border bg-harbor-secondary text-text-secondary hover:border-danger/35',
  },
  warning: {
    on: 'border-warning bg-warning-muted text-warning',
    off: 'border-border bg-harbor-secondary text-text-secondary hover:border-warning/35',
  },
  accent: {
    on: 'border-accent bg-accent-muted text-accent',
    off: 'border-border bg-harbor-secondary text-text-secondary hover:border-accent/35',
  },
  accent2: {
    on: 'border-accent-2 bg-accent-2-muted text-accent-2',
    off: 'border-border bg-harbor-secondary text-text-secondary hover:border-accent-2/35',
  },
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
      <div className="max-w-[1080px] mx-auto space-y-4">
        <Skeleton className="h-20" />
        <Skeleton className="h-64" />
      </div>
    )
  }

  if (isError || !dispute) {
    return (
      <div className="max-w-[1080px] mx-auto">
        <Notification type="danger">{error ?? 'Спор не найден'}</Notification>
      </div>
    )
  }

  const statusMeta = getDisputeStatusMeta(dispute.status)

  return (
    <div className="max-w-[1080px] mx-auto">
      <ScreenHeader
        title={`Спор #${dispute.id}`}
        subtitle={dispute.reason.replace(/_/g, ' ')}
        action={
          <>
            <Button
              variant="secondary"
              size="sm"
              iconLeft="arrow-left"
              onClick={() => navigate('/admin/disputes')}
            >
              К списку
            </Button>
            <Button
              variant="primary"
              size="sm"
              iconRight="arrow-right"
              onClick={() => navigate(`/own/requests/${dispute.placement_request_id}`)}
            >
              Перейти к кампании #{dispute.placement_request_id}
            </Button>
          </>
        }
      />

      <div className="mb-5 inline-flex items-center gap-2 text-[10.5px] font-bold tracking-[0.08em] uppercase py-1 px-2 rounded">
        <span className={`inline-flex items-center gap-1.5 py-1 px-2 rounded ${DISPUTE_TONE_CLASSES[statusMeta.tone]}`}>
          <Icon name={statusMeta.icon} size={12} />
          {statusMeta.label}
        </span>
        <span className="text-text-tertiary">
          Создан {formatDateTimeMSK(dispute.created_at)} МСК
        </span>
      </div>

      <div className="grid gap-4 lg:grid-cols-2 mb-4">
        <div className="bg-harbor-card border border-border rounded-xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <Icon name="users" size={14} className="text-text-tertiary" />
            <span className="font-display text-[14px] font-semibold text-text-primary">
              Рекламодатель #{dispute.advertiser_id}
            </span>
          </div>
          {dispute.advertiser_comment ? (
            <p className="text-[13.5px] leading-[1.55] text-text-secondary whitespace-pre-wrap">
              {dispute.advertiser_comment}
            </p>
          ) : (
            <p className="text-[12.5px] text-text-tertiary italic">Комментарий не оставлен</p>
          )}
        </div>
        <div className="bg-harbor-card border border-border rounded-xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <Icon name="channels" size={14} className="text-text-tertiary" />
            <span className="font-display text-[14px] font-semibold text-text-primary">
              Владелец #{dispute.owner_id}
            </span>
          </div>
          {dispute.owner_explanation ? (
            <p className="text-[13.5px] leading-[1.55] text-text-secondary whitespace-pre-wrap">
              {dispute.owner_explanation}
            </p>
          ) : (
            <p className="text-[12.5px] text-text-tertiary italic">Ответ ещё не получен</p>
          )}
        </div>
      </div>

      {dispute.resolution ? (
        <div className="bg-harbor-card border border-success/25 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <Icon name="verified" size={14} className="text-success" variant="fill" />
            <span className="font-display text-[14px] font-semibold text-text-primary">
              Решение
            </span>
          </div>
          <div className="grid gap-2.5 text-[13px]">
            <DetailRow label="Решение">
              <span className="text-text-primary font-semibold">
                {dispute.resolution.replace(/_/g, ' ')}
              </span>
            </DetailRow>
            {dispute.resolution_comment && (
              <DetailRow label="Комментарий">
                <span className="text-text-primary">{dispute.resolution_comment}</span>
              </DetailRow>
            )}
            <DetailRow label="Возврат рекламодателю">
              <span className="font-mono tabular-nums text-text-primary">
                {dispute.advertiser_refund_pct}%
              </span>
            </DetailRow>
            <DetailRow label="Выплата владельцу">
              <span className="font-mono tabular-nums text-text-primary">
                {dispute.owner_payout_pct}%
              </span>
            </DetailRow>
          </div>
        </div>
      ) : (
        <div className="bg-harbor-card border border-border rounded-xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <Icon name="audit" size={14} className="text-accent" />
            <span className="font-display text-[14px] font-semibold text-text-primary">
              Разрешить спор
            </span>
          </div>

          <div className="grid gap-2 sm:grid-cols-2">
            {(['owner_fault', 'advertiser_fault', 'technical', 'partial'] as Resolution[]).map((res) => {
              const meta = RESOLUTION_META[res]
              const on = resolution === res
              const cls = on ? resolutionToneClasses[meta.tone].on : resolutionToneClasses[meta.tone].off
              return (
                <button
                  key={res}
                  type="button"
                  onClick={() => setResolution(res)}
                  className={`flex items-start gap-3 p-3 rounded-lg border text-left transition-all ${cls}`}
                >
                  <span className="grid place-items-center w-9 h-9 rounded-md flex-shrink-0 bg-harbor-elevated">
                    <Icon name={meta.icon} size={14} />
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="font-display text-[13.5px] font-semibold">{meta.label}</div>
                    <div className="text-[11.5px] opacity-80 mt-0.5">{meta.description}</div>
                  </div>
                </button>
              )
            })}
          </div>

          {resolution === 'partial' && (
            <div className="mt-4 bg-harbor-secondary border border-border rounded-lg p-4">
              <label className="block text-[12.5px] font-semibold text-text-secondary mb-2">
                Возврат рекламодателю:{' '}
                <span className="font-mono tabular-nums text-accent">{customSplit}%</span>
              </label>
              <input
                type="range"
                min={0}
                max={100}
                value={customSplit}
                onChange={(e) => setCustomSplit(Number(e.target.value))}
                className="w-full accent-accent"
              />
              <div className="flex justify-between text-[11.5px] text-text-tertiary mt-1 font-mono tabular-nums">
                <span>Рекламодатель: {customSplit}%</span>
                <span>Владелец: {100 - customSplit}%</span>
              </div>
            </div>
          )}

          <div className="mt-4">
            <Textarea
              rows={3}
              value={adminComment}
              onChange={setAdminComment}
              placeholder="Комментарий администратора (необязательно)"
            />
          </div>

          <Button
            variant="primary"
            iconLeft="check"
            fullWidth
            className="mt-4"
            loading={resolveMutation.isPending}
            disabled={!resolution || resolveMutation.isPending}
            onClick={handleResolve}
          >
            Разрешить спор
          </Button>
        </div>
      )}
    </div>
  )
}

function DetailRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <span className="text-text-secondary">{label}</span>
      <span className="text-right">{children}</span>
    </div>
  )
}
