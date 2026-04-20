import { useNavigate } from 'react-router-dom'
import { StepIndicator, ChannelCard, Button, StatusPill, Skeleton, EmptyState } from '@shared/ui'
import { useAvailableChannels } from '@/hooks/useCampaignQueries'
import { formatCurrency } from '@/lib/constants'
import { useCampaignWizardStore } from '@/stores/campaignWizardStore'

export default function CampaignChannels() {
  const navigate = useNavigate()
  const store = useCampaignWizardStore()

  const { data: channels = [], isLoading } = useAvailableChannels(store.category ?? undefined)

  const totalBase = store.selectedChannels.reduce(
    (sum, ch) => sum + parseFloat(ch.settings.price_per_post),
    0,
  )

  const handleToggle = (channelId: number) => {
    const channel = channels.find((c) => c.id === channelId)
    if (!channel) return
    store.toggleChannel(channel)
  }

  return (
    <div className="space-y-6">
      <StepIndicator
        total={6}
        current={2}
        labels={['Тематика', 'Каналы', 'Формат', 'Текст', 'Условия', 'Оплата']}
      />

      {isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
      ) : channels.length === 0 ? (
        <EmptyState
          icon="📭"
          title="Каналы не найдены"
          description="В выбранной категории пока нет доступных каналов"
        />
      ) : (
        <div className="space-y-3">
          {channels.map((channel) => {
            const isSelected = store.selectedChannels.some((c) => c.id === channel.id)

            return (
              <ChannelCard
                key={channel.id}
                name={channel.title}
                username={channel.username ?? null}
                subscribers={channel.member_count.toLocaleString('ru-RU')}
                category={channel.category ?? 'Без категории'}
                price={formatCurrency(channel.settings.price_per_post)}
                status="active"
                isSelected={isSelected}
                onClick={() => handleToggle(channel.id)}
                action={
                  isSelected
                    ? <StatusPill status="success">✓</StatusPill>
                    : <Button variant="success" size="sm">Выбрать</Button>
                }
              />
            )
          })}
        </div>
      )}

      {/* Summary bar */}
      <div className="sticky bottom-0 bg-harbor-card border-t border-border -mx-4 px-4 py-4 sm:mx-0 sm:rounded-lg sm:border sm:px-5">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm text-text-secondary">
            Выбрано каналов: {store.selectedChannels.length}
          </span>
          <span className="text-lg font-bold text-text-primary">
            Итого (пост 24ч): {formatCurrency(totalBase)}
          </span>
        </div>
        <Button
          variant="primary"
          fullWidth
          disabled={store.selectedChannels.length === 0}
          onClick={() => {
            store.nextStep()
            navigate('/adv/campaigns/new/format')
          }}
        >
          Далее →
        </Button>
      </div>
    </div>
  )
}
