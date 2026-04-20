import { useNavigate } from 'react-router-dom'
import { ChannelCard, Button, StatusPill, Skeleton, EmptyState, Icon } from '@shared/ui'
import { useAvailableChannels } from '@/hooks/useCampaignQueries'
import { formatCurrency } from '@/lib/constants'
import { useCampaignWizardStore } from '@/stores/campaignWizardStore'
import { CampaignWizardShell } from './_shell'

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

  const disabled = store.selectedChannels.length === 0

  return (
    <CampaignWizardShell
      step={2}
      title="Выберите каналы"
      subtitle={`Отмечено: ${store.selectedChannels.length} · базовая цена за пост 24ч: ${formatCurrency(totalBase)}`}
      footer={
        <>
          <Button
            variant="secondary"
            iconLeft="arrow-left"
            onClick={() => navigate('/adv/campaigns/new/category')}
          >
            Назад
          </Button>
          <div className="flex-1 hidden sm:flex items-center justify-center gap-2 text-[12.5px] text-text-tertiary">
            <Icon name="channels" size={13} />
            {store.selectedChannels.length} каналов · {formatCurrency(totalBase)}
          </div>
          <Button
            variant="primary"
            iconRight="arrow-right"
            disabled={disabled}
            onClick={() => {
              store.nextStep()
              navigate('/adv/campaigns/new/format')
            }}
          >
            Далее — формат
          </Button>
        </>
      }
    >
      {isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
      ) : channels.length === 0 ? (
        <EmptyState
          icon="channels"
          title="Каналы не найдены"
          description="В выбранной категории пока нет доступных каналов. Вернитесь к шагу «Тематика» и попробуйте «Все каналы»."
          action={{
            label: 'Изменить тематику',
            onClick: () => navigate('/adv/campaigns/new/category'),
          }}
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
                  isSelected ? (
                    <StatusPill status="success">В списке</StatusPill>
                  ) : (
                    <Button variant="secondary" size="sm" iconLeft="plus">
                      Выбрать
                    </Button>
                  )
                }
              />
            )
          })}
        </div>
      )}
    </CampaignWizardShell>
  )
}
