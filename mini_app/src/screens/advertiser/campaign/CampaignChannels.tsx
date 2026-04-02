import { useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { StepIndicator, ChannelCard, Button, StatusPill, Skeleton, EmptyState } from '@/components/ui'
import { useAvailableChannels } from '@/hooks/queries'
import { formatCurrency } from '@/lib/formatters'
import { useCampaignWizardStore } from '@/stores/campaignWizardStore'
import styles from './CampaignChannels.module.css'

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
    <ScreenShell noPadding>
      <div className={styles.scrollArea}>
        <div className={styles.header}>
          <StepIndicator
            total={6}
            current={1}
            labels={['', `Шаг 2 — Выберите каналы (${store.category ? store.category + ' тематика' : 'все тематики'})`]}
          />
        </div>

        <div className={styles.list}>
          {isLoading ? (
            <>
              <Skeleton height={100} radius="md" />
              <Skeleton height={100} radius="md" />
              <Skeleton height={100} radius="md" />
            </>
          ) : channels.length === 0 ? (
            <EmptyState
              icon="📭"
              title="Каналы не найдены"
              description="В выбранной категории пока нет доступных каналов"
            />
          ) : (
            channels.map((channel) => {
              const isSelected = store.selectedChannels.some((c) => c.id === channel.id)

              return (
                <div key={channel.id} className={styles.channelWrap}>
                  <ChannelCard
                    name={channel.title}
                    username={channel.username}
                    subscribers={channel.member_count.toLocaleString('ru-RU')}
                    category={channel.category}
                    price={formatCurrency(channel.settings.price_per_post)}
                    status="active"
                    onClick={() => handleToggle(channel.id)}
                  />
                  <div className={styles.channelActions}>
                    {isSelected ? (
                      <StatusPill status="success">✓ Выбран</StatusPill>
                    ) : (
                      <>
                        <Button variant="success" size="sm" onClick={() => handleToggle(channel.id)}>
                          ✅ Выбрать
                        </Button>
                        <Button variant="secondary" size="sm" onClick={() => {}}>
                          ❌ Пропустить
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              )
            })
          )}
        </div>
      </div>

      <div className={styles.stickyBottom}>
        <div className={styles.summary}>
          <span className={styles.summaryLabel}>Выбрано каналов: {store.selectedChannels.length}</span>
          <span className={styles.summaryTotal}>Итого (пост 24ч): {formatCurrency(totalBase)}</span>
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
    </ScreenShell>
  )
}
