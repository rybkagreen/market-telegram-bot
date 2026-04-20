import { useNavigate } from 'react-router-dom'
import { FormatSelector, Notification, Button } from '@shared/ui'
import { PUBLICATION_FORMATS, canUsePlan, calcFormatPrice, PLAN_INFO } from '@/lib/constants'
import { formatCurrency } from '@/lib/constants'
import { useMe } from '@/hooks/queries'
import { useCampaignWizardStore } from '@/stores/campaignWizardStore'
import type { PublicationFormat } from '@/stores/campaignWizardStore'
import { CampaignWizardShell } from './_shell'

export default function CampaignFormat() {
  const navigate = useNavigate()
  const store = useCampaignWizardStore()
  const { data: me } = useMe()

  const userPlan = me?.plan ?? 'free'

  const avgBasePrice =
    store.selectedChannels.length > 0
      ? store.selectedChannels.reduce((sum, ch) => sum + parseFloat(ch.settings.price_per_post), 0) /
        store.selectedChannels.length
      : 1500

  const hasUnavailable = Object.values(PUBLICATION_FORMATS).some(
    (fmt) => !canUsePlan(userPlan, fmt.minPlan),
  )

  const formats = Object.entries(PUBLICATION_FORMATS).map(([key, fmt]) => {
    const available = canUsePlan(userPlan, fmt.minPlan)
    const price = calcFormatPrice(avgBasePrice, key as PublicationFormat)
    return {
      id: key,
      label: fmt.name,
      description: available
        ? fmt.description
        : `Недоступно на тарифе ${PLAN_INFO[userPlan]?.displayName ?? userPlan}`,
      icon: fmt.icon,
      price: formatCurrency(price),
      disabled: !available,
    }
  })

  const handleSelect = (key: string) => {
    const fmt = key as PublicationFormat
    store.setFormat(fmt)
    store.selectedChannels.forEach((ch) => {
      const basePrice = parseFloat(ch.settings.price_per_post)
      store.setProposedPrice(ch.id, calcFormatPrice(basePrice, fmt))
    })
  }

  return (
    <CampaignWizardShell
      step={3}
      title="Выберите формат публикации"
      subtitle={`Базовая цена: ${formatCurrency(Math.round(avgBasePrice))} · множитель зависит от формата.`}
      footer={
        <>
          <Button
            variant="secondary"
            iconLeft="arrow-left"
            onClick={() => navigate('/adv/campaigns/new/channels')}
          >
            Назад
          </Button>
          <div className="flex-1" />
          <Button
            variant="primary"
            iconRight="arrow-right"
            disabled={store.format === null}
            onClick={() => {
              store.nextStep()
              navigate('/adv/campaigns/new/text')
            }}
          >
            Далее — текст
          </Button>
        </>
      }
    >
      <FormatSelector
        formats={formats}
        selected={store.format ?? undefined}
        onSelect={handleSelect}
      />

      {hasUnavailable && (
        <Notification type="warning">
          Некоторые форматы доступны только на тарифах Pro и Agency.
        </Notification>
      )}
    </CampaignWizardShell>
  )
}
