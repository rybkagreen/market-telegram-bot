import { useNavigate, useParams } from 'react-router-dom'
import {
  Notification,
  Button,
  Skeleton,
  Icon,
  ScreenHeader,
} from '@shared/ui'
import type { IconName } from '@shared/ui'
import { formatCompact, CATEGORIES, formatDateMSK } from '@/lib/constants'
import { useMyChannels } from '@/hooks/useChannelQueries'
import { useDeleteChannel, useActivateChannel } from '@/hooks/useChannelSettings'

const CATEGORY_OPTIONS = CATEGORIES.map((c) => ({ key: c.key, label: c.name, emoji: c.emoji }))

export default function OwnChannelDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const numId = id ? parseInt(id, 10) : null
  const { data: channels, isLoading } = useMyChannels()
  const deleteChannel = useDeleteChannel()
  const activateChannel = useActivateChannel()

  const channel = channels?.find((c) => c.id === numId) ?? null

  if (isLoading) {
    return (
      <div className="max-w-[1080px] mx-auto space-y-4">
        <Skeleton className="h-20" />
        <Skeleton className="h-32" />
        <Skeleton className="h-24" />
      </div>
    )
  }

  if (!channel) {
    return (
      <div className="max-w-[1080px] mx-auto">
        <Notification type="danger">Канал не найден</Notification>
      </div>
    )
  }

  const handleDeleteChannel = () => {
    if (!confirm(`Скрыть канал «${channel.title}» от рекламодателей?`)) return
    deleteChannel.mutate(channel.id, {
      onSuccess: () => navigate('/own/channels'),
      onError: () => alert('Не удалось скрыть канал. Попробуйте позже.'),
    })
  }

  const handleActivateChannel = () => {
    if (!confirm(`Восстановить канал «${channel.title}»? Он снова станет виден рекламодателям.`))
      return
    activateChannel.mutate(channel.id, {
      onError: () => alert('Не удалось восстановить канал. Попробуйте позже.'),
    })
  }

  const categoryInfo = channel.category
    ? CATEGORY_OPTIONS.find((c) => c.key === channel.category)
    : null

  return (
    <div className="max-w-[1080px] mx-auto">
      <ScreenHeader
        crumbs={['Главная', 'Владелец', 'Каналы', `@${channel.username}`]}
        title={channel.title}
        subtitle={`@${channel.username} · ${categoryInfo ? `${categoryInfo.emoji} ${categoryInfo.label}` : 'без категории'}`}
        action={
          <Button
            variant="secondary"
            iconLeft="arrow-left"
            onClick={() => navigate('/own/channels')}
          >
            К списку
          </Button>
        }
      />

      <div className="bg-harbor-card border border-border rounded-xl p-5 mb-5 relative overflow-hidden">
        <div
          className={`absolute top-0 left-0 right-0 h-[3px] ${channel.is_active ? 'bg-gradient-to-r from-accent to-accent-2' : 'bg-harbor-elevated'}`}
        />
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-[14px] bg-accent-muted grid place-items-center font-display text-[26px] font-bold text-accent flex-shrink-0">
            {channel.title[0]?.toUpperCase() ?? '#'}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-display text-[20px] font-bold tracking-[-0.02em] text-text-primary truncate">
                {channel.title}
              </span>
              <span
                className={`text-[10.5px] font-bold tracking-[0.08em] uppercase py-1 px-2 rounded ${channel.is_active ? 'bg-success-muted text-success' : 'bg-harbor-elevated text-text-tertiary'}`}
              >
                {channel.is_active ? 'Активен' : 'Скрыт'}
              </span>
            </div>
            <div className="text-[13px] text-text-tertiary mt-0.5">@{channel.username}</div>
          </div>
        </div>

        <div
          className="grid gap-3.5 mt-4"
          style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))' }}
        >
          <StatTile
            icon="audience"
            tone="accent"
            label="Подписчики"
            value={formatCompact(channel.member_count)}
          />
          <StatTile
            icon="star"
            tone="warning"
            label="Рейтинг"
            value={channel.rating.toFixed(1)}
          />
          <StatTile
            icon="category"
            tone="accent2"
            label="Категория"
            value={categoryInfo ? categoryInfo.label : '—'}
          />
          <StatTile
            icon="calendar"
            tone="neutral"
            label="Создан"
            value={formatDateMSK(channel.created_at)}
          />
        </div>
      </div>

      {!channel.category && (
        <div className="mb-5">
          <Notification type="warning">
            Канал без категории — он не виден рекламодателям. Выберите категорию в настройках.
          </Notification>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 mb-5">
        <ActionTile
          icon="settings"
          title="Настройки канала"
          description="Цены, форматы, расписание"
          onClick={() => navigate(`/own/channels/${channel.id}/settings`)}
        />
        <ActionTile
          icon="requests"
          title="Заявки канала"
          description="Ожидают вашего ответа"
          onClick={() => navigate('/own/requests')}
        />
      </div>

      {channel.is_active ? (
        <div className="bg-harbor-card border border-danger/35 rounded-xl p-5">
          <div className="flex items-start gap-3">
            <span className="grid place-items-center w-10 h-10 rounded-[10px] bg-danger-muted text-danger flex-shrink-0">
              <Icon name="eye-off" size={18} />
            </span>
            <div className="flex-1">
              <div className="font-display text-[14px] font-semibold text-danger">Опасная зона</div>
              <div className="text-[12.5px] text-text-tertiary mt-1 mb-3">
                Канал будет скрыт от рекламодателей. Данные сохранятся — можно восстановить.
              </div>
              <Button
                variant="danger"
                size="sm"
                iconLeft="eye-off"
                loading={deleteChannel.isPending}
                disabled={deleteChannel.isPending}
                onClick={handleDeleteChannel}
              >
                Скрыть канал
              </Button>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-harbor-card border border-success/35 rounded-xl p-5">
          <div className="flex items-start gap-3">
            <span className="grid place-items-center w-10 h-10 rounded-[10px] bg-success-muted text-success flex-shrink-0">
              <Icon name="refresh" size={18} />
            </span>
            <div className="flex-1">
              <div className="font-display text-[14px] font-semibold text-success">
                Канал неактивен
              </div>
              <div className="text-[12.5px] text-text-tertiary mt-1 mb-3">
                Канал скрыт от рекламодателей. Восстановите, чтобы он снова стал виден.
              </div>
              <Button
                variant="primary"
                size="sm"
                iconLeft="refresh"
                loading={activateChannel.isPending}
                disabled={activateChannel.isPending}
                onClick={handleActivateChannel}
              >
                Восстановить канал
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

const statToneBg: Record<'success' | 'warning' | 'accent' | 'accent2' | 'neutral', string> = {
  success: 'bg-success-muted text-success',
  warning: 'bg-warning-muted text-warning',
  accent: 'bg-accent-muted text-accent',
  accent2: 'bg-accent-2-muted text-accent-2',
  neutral: 'bg-harbor-elevated text-text-tertiary',
}

function StatTile({
  icon,
  tone,
  label,
  value,
}: {
  icon: IconName
  tone: 'success' | 'warning' | 'accent' | 'accent2' | 'neutral'
  label: string
  value: string
}) {
  return (
    <div className="bg-harbor-secondary border border-border rounded-[10px] p-3 flex gap-3 items-center">
      <span className={`grid place-items-center w-9 h-9 rounded-md flex-shrink-0 ${statToneBg[tone]}`}>
        <Icon name={icon} size={15} />
      </span>
      <div className="min-w-0">
        <div className="text-[10.5px] uppercase tracking-wider text-text-tertiary">{label}</div>
        <div className="font-mono tabular-nums font-semibold text-text-primary text-[14px] truncate">
          {value}
        </div>
      </div>
    </div>
  )
}

function ActionTile({
  icon,
  title,
  description,
  onClick,
}: {
  icon: IconName
  title: string
  description: string
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="text-left bg-harbor-card border border-border rounded-xl p-5 flex items-center gap-3 hover:-translate-y-0.5 hover:border-accent/40 transition-all"
    >
      <span className="grid place-items-center w-10 h-10 rounded-[10px] bg-accent-muted text-accent flex-shrink-0">
        <Icon name={icon} size={18} />
      </span>
      <div className="flex-1 min-w-0">
        <div className="font-display text-[14px] font-semibold text-text-primary">{title}</div>
        <div className="text-[12px] text-text-tertiary truncate">{description}</div>
      </div>
      <Icon name="chevron-right" size={14} className="text-text-tertiary" />
    </button>
  )
}
