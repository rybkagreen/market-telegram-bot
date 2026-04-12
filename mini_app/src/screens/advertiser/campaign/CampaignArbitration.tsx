import { useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { StepIndicator, ArbitrationPanel, FeeBreakdown, Button } from '@/components/ui'
import { PUBLICATION_FORMATS } from '@/lib/constants'
import { formatCurrency, calcFormatPrice } from '@/lib/formatters'
import { useCampaignWizardStore } from '@/stores/campaignWizardStore'
import { useHaptic } from '@/hooks/useHaptic'
import { useCreatePlacement } from '@/hooks/queries'
import styles from './CampaignArbitration.module.css'

export default function CampaignArbitration() {
  const navigate = useNavigate()
  const haptic = useHaptic()
  const store = useCampaignWizardStore()
  const { mutateAsync: createPlacement, isPending } = useCreatePlacement()

  const format = store.format
  const formatInfo = format ? PUBLICATION_FORMATS[format] : null

  const tomorrow = new Date()
  tomorrow.setDate(tomorrow.getDate() + 1)
  const defaultDate = tomorrow.toISOString().substring(0, 10)

  const handleSubmit = async () => {
    if (!format || store.selectedChannels.length === 0) return
    haptic.success()
    const results = await Promise.all(
      store.selectedChannels.map((ch) => {
        const schedule = store.proposedSchedules[ch.id] ?? `${defaultDate}T14:00`
        const basePrice = parseFloat(ch.settings.price_per_post)
        const ownerPrice = Math.round(calcFormatPrice(basePrice, format))
        const price = store.proposedPrices[ch.id] ?? ownerPrice
        return createPlacement({
          channel_id: ch.id,
          publication_format: format,
          ad_text: store.adText,
          proposed_price: price,
          proposed_schedule: `${schedule}:00+03:00`,
          is_test: store.isTest,
        })
      }),
    )
    store.reset()
    const firstId = results[0]?.id ?? null
    navigate(`/adv/campaigns/${firstId}/waiting`)
  }

  const feeRows = store.selectedChannels.map((ch) => ({
    label: `@${ch.username}`,
    value: formatCurrency(store.proposedPrices[ch.id] ?? 0),
  }))

  return (
    <ScreenShell>
      <StepIndicator
        total={6}
        current={4}
        labels={['', '', '', '', 'Шаг 5 — Условия размещения']}
      />

      {store.selectedChannels.map((ch) => {
        const basePrice = parseFloat(ch.settings.price_per_post)
        const ownerPrice = format ? calcFormatPrice(basePrice, format) : basePrice
        const currentProposed = store.proposedPrices[ch.id] ?? ownerPrice
        const currentSchedule = store.proposedSchedules[ch.id] ?? `${defaultDate}T14:00`

        const currentDateTime = currentSchedule.includes('T') ? currentSchedule : `${defaultDate}T${currentSchedule}`
        const [currentDatePart, currentTimePart] = currentDateTime.split('T')

        return (
          <ArbitrationPanel
            key={ch.id}
            title={`@${ch.username}`}
            status={formatInfo?.name ?? ''}
          >
            <div className={styles.rows}>
              <div className={styles.row}>
                <span className={styles.rowLabel}>💰 Цена владельца</span>
                <span className={styles.rowValue}>{formatCurrency(ownerPrice)}</span>
              </div>
              <div className={styles.row}>
                <span className={styles.rowLabel}>💬 Ваше предложение</span>
                <input
                  type="number"
                  className={styles.priceInput}
                  value={currentProposed}
                  onChange={(e) =>
                    store.setProposedPrice(ch.id, parseInt(e.target.value, 10) || 0)
                  }
                />
              </div>
              <div className={styles.row}>
                <span className={styles.rowLabel}>📅 Дата публикации</span>
                <input
                  type="date"
                  className={styles.timeInput}
                  value={currentDatePart ?? defaultDate}
                  min={defaultDate}
                  onChange={(e) =>
                    store.setProposedSchedule(ch.id, `${e.target.value}T${currentTimePart ?? '14:00'}`)
                  }
                />
              </div>
              <div className={styles.row}>
                <span className={styles.rowLabel}>🕐 Время публикации</span>
                <input
                  type="time"
                  className={styles.timeInput}
                  value={currentTimePart ?? '14:00'}
                  onChange={(e) =>
                    store.setProposedSchedule(ch.id, `${currentDatePart ?? defaultDate}T${e.target.value}`)
                  }
                />
              </div>
              <div className={styles.row}>
                <span className={styles.rowLabel}>📈 Частота</span>
                <span className={styles.rowValue}>1 пост</span>
              </div>
            </div>
          </ArbitrationPanel>
        )
      })}

      {store.selectedChannels.length === 0 && (
        <p className={styles.empty}>Нет выбранных каналов</p>
      )}

      <div className={styles.breakdown}>
        <FeeBreakdown
          rows={feeRows}
          total={{ label: 'Итого к оплате', value: formatCurrency(store.getTotalPrice()) }}
        />
      </div>

      <div className={styles.buttons}>
        <Button variant="primary" fullWidth onClick={() => void handleSubmit()} disabled={isPending}>
          {isPending ? '⏳ Отправка...' : '📤 Отправить заявку'}
        </Button>
        <Button variant="secondary" fullWidth onClick={() => window.history.back()}>
          🔙 Назад
        </Button>
      </div>
    </ScreenShell>
  )
}
