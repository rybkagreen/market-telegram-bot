import { useNavigate, useParams } from 'react-router-dom'
import { Card, Notification, Button, Skeleton } from '@shared/ui'
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
      <div className="space-y-4">
        <Skeleton className="h-20" />
        <Skeleton className="h-32" />
        <Skeleton className="h-24" />
      </div>
    )
  }

  if (!channel) {
    return <Notification type="danger">Канал не найден</Notification>
  }

  const handleDeleteChannel = () => {
    if (confirm(`Скрыть канал "${channel.title}" от рекламодателей?`)) {
      deleteChannel.mutate(channel.id, {
        onSuccess: () => {
          navigate('/own/channels')
        },
        onError: () => {
          alert('Не удалось скрыть канал. Попробуйте позже.')
        },
      })
    }
  }

  const handleActivateChannel = () => {
    if (confirm(`Восстановить канал "${channel.title}"? Он снова станет виден рекламодателям.`)) {
      activateChannel.mutate(channel.id, {
        onError: () => {
          alert('Не удалось восстановить канал. Попробуйте позже.')
        },
      })
    }
  }

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-4">
        <div className="w-16 h-16 rounded-full bg-accent-muted flex items-center justify-center text-2xl font-bold text-accent shrink-0">
          {channel.title[0]?.toUpperCase() ?? '📺'}
        </div>
        <div className="flex-1 min-w-0">
          <h1 className="text-2xl font-display font-bold text-text-primary">{channel.title}</h1>
          <p className="text-text-secondary">@{channel.username}</p>
        </div>
        <span className={`px-3 py-1.5 rounded-full text-sm font-medium shrink-0 ${
          channel.is_active ? 'bg-success-muted text-success' : 'bg-harbor-elevated text-text-tertiary'
        }`}>
          {channel.is_active ? '✅ Активен' : '⏸ Неактивен'}
        </span>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Card className="p-4 text-center">
          <p className="text-sm text-text-secondary">Подписчиков</p>
          <p className="text-2xl font-bold text-text-primary mt-1 tabular-nums">{formatCompact(channel.member_count)}</p>
        </Card>
        <Card className="p-4 text-center">
          <p className="text-sm text-text-secondary">Рейтинг</p>
          <p className="text-2xl font-bold text-warning mt-1">{channel.rating.toFixed(1)} ⭐</p>
        </Card>
        <Card className="p-4 text-center">
          <p className="text-sm text-text-secondary">Категория</p>
          <p className="text-lg font-medium text-text-primary mt-1">
            {CATEGORY_OPTIONS.find((c) => c.key === channel.category)?.emoji ?? '—'}{' '}
            {CATEGORY_OPTIONS.find((c) => c.key === channel.category)?.label ?? 'Не выбрана'}
          </p>
        </Card>
        <Card className="p-4 text-center">
          <p className="text-sm text-text-secondary">Создан</p>
          <p className="text-lg font-medium text-text-primary mt-1 tabular-nums">
            {formatDateMSK(channel.created_at)}
          </p>
        </Card>
      </div>

      {/* Actions */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Card className="p-5 cursor-pointer hover:shadow-lg transition-shadow" onClick={() => navigate(`/own/channels/${channel.id}/settings`)}>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-accent-muted flex items-center justify-center shrink-0">
              <svg className="w-5 h-5 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.24-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.507 6.507 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.753-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
              </svg>
            </div>
            <div>
              <p className="font-semibold text-text-primary">Настройки канала</p>
              <p className="text-sm text-text-tertiary">Цены, форматы, расписание</p>
            </div>
          </div>
        </Card>
        <Card className="p-5 cursor-pointer hover:shadow-lg transition-shadow" onClick={() => navigate('/own/requests')}>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-accent-muted flex items-center justify-center shrink-0">
              <svg className="w-5 h-5 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 0 0 2.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 0 0-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15a2.25 2.25 0 0 1 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25ZM6.75 12h.008v.008H6.75V12Zm0 3h.008v.008H6.75V15Zm0 3h.008v.008H6.75V18Z" />
              </svg>
            </div>
            <div>
              <p className="font-semibold text-text-primary">Заявки канала</p>
              <p className="text-sm text-text-tertiary">Ожидают вашего ответа</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Danger / Restore zone */}
      {channel.is_active ? (
        <Card className="p-5 border border-danger/30">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-lg bg-danger-muted flex items-center justify-center shrink-0">
              <svg className="w-5 h-5 text-danger" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
              </svg>
            </div>
            <div className="flex-1">
              <p className="font-semibold text-danger">Опасная зона</p>
              <p className="text-sm text-text-tertiary mt-1 mb-3">Канал будет скрыт от рекламодателей. Данные сохранятся.</p>
              <Button
                variant="danger"
                size="sm"
                loading={deleteChannel.isPending}
                disabled={deleteChannel.isPending}
                onClick={handleDeleteChannel}
              >
                🗑️ Скрыть канал
              </Button>
            </div>
          </div>
        </Card>
      ) : (
        <Card className="p-5 border border-success/30">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-lg bg-success-muted flex items-center justify-center shrink-0">
              <svg className="w-5 h-5 text-success" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 26L15.99 22H8.01l-.033 4H4.007A2.007 2.007 0 0 1 2 20.007V4.007C2 2.9 2.9 2 4.007 2h15.986C21.1 2 22 2.9 22 4.007v15.986C22 21.1 21.1 22 19.993 22h-3.97Z" />
              </svg>
            </div>
            <div className="flex-1">
              <p className="font-semibold text-success">Канал неактивен</p>
              <p className="text-sm text-text-tertiary mt-1 mb-3">Канал скрыт от рекламодателей. Восстановите, чтобы он снова стал виден.</p>
              <Button
                variant="primary"
                size="sm"
                loading={activateChannel.isPending}
                disabled={activateChannel.isPending}
                onClick={handleActivateChannel}
              >
                ♻️ Восстановить канал
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* Warning if no category */}
      {!channel.category && (
        <Notification type="warning">
          ⚠️ Канал без категории — он не виден рекламодателям. Выберите категорию в настройках.
        </Notification>
      )}

      <Button variant="ghost" fullWidth onClick={() => navigate('/own/channels')}>
        ← К списку каналов
      </Button>
    </div>
  )
}
