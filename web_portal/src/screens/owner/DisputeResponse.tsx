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
import { PUBLICATION_FORMATS } from '@/lib/constants'
import { formatCurrency } from '@/lib/constants'
import { usePlacement } from '@/hooks/useCampaignQueries'
import { useDisputeById, useReplyToDispute } from '@/hooks/useDisputeQueries'
import {
  DISPUTE_TONE_CLASSES,
  getDisputeStatusMeta,
  getRoleAwareStatusLabel,
} from '@/lib/disputeLabels'

const MIN_REPLY = 20

export default function DisputeResponse() {
  const { id } = useParams()
  const navigate = useNavigate()

  const numId = id ? parseInt(id, 10) : null
  const { data: dispute, isLoading: disputeLoading } = useDisputeById(numId)
  const { data: placement, isLoading: placementLoading } = usePlacement(
    dispute ? dispute.placement_request_id : null,
  )
  const { mutate: replyToDispute, isPending } = useReplyToDispute()

  const [ownerReply, setOwnerReply] = useState('')

  const isLoading = disputeLoading || placementLoading

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

  const fmt = placement ? PUBLICATION_FORMATS[placement.publication_format] : null
  const tone = getDisputeStatusMeta(dispute.status).tone
  const ownerStatusLabel = getRoleAwareStatusLabel(dispute.status, 'owner')

  const handleSubmit = () => {
    if (ownerReply.length < MIN_REPLY) return
    replyToDispute(
      { id: dispute.id, comment: ownerReply },
      { onSuccess: () => navigate('/own/requests') },
    )
  }

  return (
    <div className="max-w-[1080px] mx-auto">
      <ScreenHeader
        title={`Спор #${dispute.id}`}
        subtitle="Ответ владельца — опишите ситуацию, чтобы администратор мог принять справедливое решение"
        action={
          <Button
            variant="ghost"
            size="sm"
            iconLeft="arrow-left"
            onClick={() => navigate('/own/requests')}
          >
            К заявкам
          </Button>
        }
      />

      <div className="mb-5">
        <Notification type={dispute.status === 'open' ? 'warning' : 'info'}>
          Статус: {ownerStatusLabel}
        </Notification>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
        <div className="space-y-4">
          {dispute.advertiser_comment && (
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
          )}

          {dispute.status === 'open' ? (
            <div className="bg-harbor-card border border-border rounded-xl p-5">
              <div className="flex items-center gap-2 mb-3">
                <Icon name="edit" size={14} className="text-accent" />
                <span className="font-display text-[14px] font-semibold text-text-primary">
                  Ваше объяснение
                </span>
              </div>
              <Textarea
                rows={5}
                value={ownerReply}
                onChange={setOwnerReply}
                placeholder={`Минимум ${MIN_REPLY} символов. Приведите факты и хронологию.`}
              />
              <p
                className={`text-[11.5px] mt-1.5 flex items-center gap-1.5 ${ownerReply.length >= MIN_REPLY ? 'text-success' : 'text-text-tertiary'}`}
              >
                <Icon
                  name={ownerReply.length >= MIN_REPLY ? 'check' : 'hourglass'}
                  size={12}
                />
                {ownerReply.length} / мин. {MIN_REPLY} символов
              </p>

              <div className="mt-3">
                <Notification type="info">
                  Подробное и честное объяснение повышает шансы на благоприятное решение.
                </Notification>
              </div>

              <Button
                variant="primary"
                iconLeft="check"
                className="mt-4"
                fullWidth
                disabled={ownerReply.length < MIN_REPLY || isPending}
                loading={isPending}
                onClick={handleSubmit}
              >
                Отправить объяснение
              </Button>
            </div>
          ) : dispute.status === 'owner_explained' ? (
            <Notification type="info">
              Ваше объяснение отправлено. Ожидание решения администратора.
            </Notification>
          ) : (
            <Notification type="info">
              Спор {ownerStatusLabel.toLowerCase()}.
            </Notification>
          )}
        </div>

        <div className="space-y-4">
          <div className="bg-harbor-card border border-border rounded-xl p-5 h-fit">
            <div className="font-display text-[14px] font-semibold text-text-primary mb-3">
              Детали размещения
            </div>
            <dl className="space-y-2.5 text-[13px]">
              {placement && (
                <>
                  <DetailRow icon="channels" label="Канал">
                    @{placement.channel?.username ?? `#${placement.channel_id}`}
                  </DetailRow>
                  {fmt && (
                    <DetailRow icon="docs" label="Формат">
                      {fmt.name}
                    </DetailRow>
                  )}
                  <DetailRow icon="ruble" label="Сумма">
                    <span className="font-mono tabular-nums font-semibold text-text-primary">
                      {formatCurrency(
                        placement.final_price ??
                          placement.counter_price ??
                          placement.proposed_price,
                      )}
                    </span>
                  </DetailRow>
                </>
              )}
              <DetailRow icon="info" label="Статус">
                <span
                  className={`text-[10.5px] font-bold tracking-[0.08em] uppercase py-0.5 px-1.5 rounded ${DISPUTE_TONE_CLASSES[tone]}`}
                >
                  {ownerStatusLabel}
                </span>
              </DetailRow>
            </dl>
          </div>
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
  icon: 'channels' | 'docs' | 'ruble' | 'info'
  label: string
  children: React.ReactNode
}) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="flex items-center gap-2 text-text-secondary">
        <Icon name={icon} size={13} className="text-text-tertiary" />
        {label}
      </span>
      <span className="text-text-primary text-right truncate">{children}</span>
    </div>
  )
}
