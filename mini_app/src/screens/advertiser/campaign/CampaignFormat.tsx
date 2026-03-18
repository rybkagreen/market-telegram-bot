import { useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { StepIndicator, FormatSelector, Notification, Button } from '@/components/ui'
import { PUBLICATION_FORMATS } from '@/lib/constants'
import { formatCurrency, calcFormatPrice, canUsePlan } from '@/lib/formatters'
import { useMe } from '@/hooks/queries'
import { useCampaignWizardStore } from '@/stores/campaignWizardStore'
import type { PublicationFormat } from '@/lib/types'
import styles from './CampaignFormat.module.css'

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
      label: fmt.name + (available ? '' : ' 🔒'),
      description: fmt.description + (available ? '' : ' — недоступно на вашем тарифе'),
      icon: fmt.icon,
      price: formatCurrency(price),
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
    <ScreenShell>
      <StepIndicator
        total={6}
        current={2}
        labels={['', '', 'Шаг 3 — Формат публикации']}
      />

      <Notification type="info">
        <span style={{ fontSize: 'var(--rh-text-sm)' }}>
          Базовая цена: {formatCurrency(Math.round(avgBasePrice))} ₽ · Множитель зависит от формата
        </span>
      </Notification>

      <div className={styles.selector}>
        <FormatSelector
          formats={formats}
          selected={store.format ?? undefined}
          onSelect={handleSelect}
        />
      </div>

      {hasUnavailable && (
        <Notification type="warning">
          <span style={{ fontSize: 'var(--rh-text-xs)' }}>
            Некоторые форматы доступны на тарифах Pro и Agency
          </span>
        </Notification>
      )}

      <Button
        variant="primary"
        fullWidth
        disabled={store.format === null}
        onClick={() => {
          store.nextStep()
          navigate('/adv/campaigns/new/text')
        }}
      >
        Далее →
      </Button>
    </ScreenShell>
  )
}
