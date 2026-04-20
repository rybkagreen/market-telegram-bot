import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Notification, Button, Skeleton, Icon, ScreenHeader, FeeBreakdown } from '@shared/ui'
import { formatCurrency, formatDateTimeMSK, formatTimeMSK } from '@/lib/constants'
import { usePlacement } from '@/hooks/useCampaignQueries'

const PLATFORM_COMMISSION = 0.15

export default function CampaignPublished() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const numId = id ? parseInt(id, 10) : null
  const { data: placement, isLoading } = usePlacement(numId)

  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const interval = setInterval(() => setNow(Date.now()), 60000)
    return () => clearInterval(interval)
  }, [])

  if (isLoading) {
    return (
      <div className="max-w-[900px] mx-auto space-y-4">
        <Skeleton className="h-20" />
        <Skeleton className="h-48" />
      </div>
    )
  }

  if (!placement) {
    return (
      <div className="max-w-[900px] mx-auto">
        <Notification type="danger">Заявка не найдена</Notification>
      </div>
    )
  }

  const price = parseFloat(
    String(placement.final_price ?? placement.counter_price ?? placement.proposed_price),
  )
  const ownerShare = price * (1 - PLATFORM_COMMISSION)
  const platformShare = price * PLATFORM_COMMISSION

  const isWithinDisputeWindow = placement.published_at
    ? (now - new Date(placement.published_at).getTime()) / 3_600_000 < 48
    : false
  const canDispute = isWithinDisputeWindow && !placement.has_dispute

  const channelLabel = placement.channel?.username
    ? `@${placement.channel.username}`
    : `#${placement.channel_id}`

  return (
    <div className="max-w-[900px] mx-auto">
      <ScreenHeader
        crumbs={['Главная', 'Рекламодатель', 'Кампании', `#${placement.id}`, 'Опубликовано']}
        title="Публикация успешна"
        subtitle={`${channelLabel} · ${placement.published_at ? formatTimeMSK(placement.published_at) + ' МСК' : '—'}`}
        action={
          <Button
            variant="secondary"
            iconLeft="arrow-left"
            onClick={() => navigate('/adv/campaigns')}
          >
            К списку
          </Button>
        }
      />

      <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
        <div className="space-y-4">
          <div className="bg-harbor-card border border-border rounded-xl p-5">
            <div className="flex items-center gap-3 mb-4">
              <span className="grid place-items-center w-11 h-11 rounded-[10px] bg-success-muted text-success">
                <Icon name="success" size={20} variant="fill" />
              </span>
              <div>
                <div className="font-display text-[15px] font-semibold text-text-primary">
                  Пост опубликован
                </div>
                <div className="text-[12.5px] text-text-tertiary">
                  Удаление: {placement.scheduled_delete_at
                    ? formatDateTimeMSK(placement.scheduled_delete_at)
                    : '—'}{' '}
                  (автоматически)
                </div>
              </div>
            </div>

            <FeeBreakdown
              rows={[
                { label: 'Владельцу (85%)', value: formatCurrency(ownerShare) },
                { label: 'Комиссия платформы (15%)', value: formatCurrency(platformShare) },
              ]}
              total={{ label: 'Итого с эскроу', value: formatCurrency(price) }}
            />
          </div>

          {placement.erid !== undefined && (
            <div className="bg-harbor-card border border-border rounded-xl p-5">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Icon name="verified" size={16} className="text-accent" />
                  <span className="font-display text-[14px] font-semibold text-text-primary">
                    Маркировка ОРД
                  </span>
                </div>
                <span
                  className={`text-[10.5px] font-bold tracking-[0.08em] uppercase py-1 px-2 rounded ${placement.erid ? 'bg-success-muted text-success' : 'bg-warning-muted text-warning'}`}
                >
                  {placement.erid ? 'Выдан' : 'Ожидается'}
                </span>
              </div>
              {placement.erid ? (
                <p className="text-[12.5px] text-text-tertiary font-mono break-all">
                  erid: {placement.erid}
                </p>
              ) : (
                <p className="text-[12.5px] text-text-tertiary">
                  Токен маркировки появится после регистрации у ОРД-оператора.
                </p>
              )}
            </div>
          )}
        </div>

        <div className="bg-harbor-card border border-border rounded-xl p-5 h-fit flex flex-col gap-2.5">
          <div className="font-display text-[14px] font-semibold text-text-primary mb-1">
            Действия
          </div>
          <Button
            variant="primary"
            fullWidth
            iconLeft="analytics"
            onClick={() => navigate('/adv/analytics')}
          >
            В статистику
          </Button>
          <Button
            variant="secondary"
            fullWidth
            iconLeft="verified"
            onClick={() => navigate(`/campaign/${placement.id}/ord`)}
          >
            Статус ОРД
          </Button>
          <Button
            variant="ghost"
            fullWidth
            iconLeft="campaign"
            onClick={() => navigate('/adv/campaigns')}
          >
            Мои кампании
          </Button>
          {canDispute && (
            <Button
              variant="danger"
              fullWidth
              iconLeft="warning"
              onClick={() => navigate(`/adv/campaigns/${placement.id}/dispute`)}
            >
              Открыть спор
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
