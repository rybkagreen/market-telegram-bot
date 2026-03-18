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

  const handleSubmit = async () => {
    if (!format || store.selectedChannels.length === 0) return
    haptic.success()
    let firstId: number | null = null
    for (const ch of store.selectedChannels) {
      const schedule = store.proposedSchedules[ch.id] ?? '14:00'
      const price = store.proposedPrices[ch.id] ?? 0
      const today = new Date().toISOString().substring(0, 10)
      const result = await createPlacement({
        channel_id: ch.id,
        publication_format: format,
        ad_text: store.adText,
        proposed_price: price,
        proposed_schedule: `${today}T${schedule}:00`,
      })
      if (firstId === null) firstId = result.id
    }
    store.reset()
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
        const currentSchedule = store.proposedSchedules[ch.id] ?? '14:00'

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
                <span className={styles.rowLabel}>📅 Время публикации</span>
                <input
                  type="time"
                  className={styles.timeInput}
                  value={currentSchedule}
                  onChange={(e) => store.setProposedSchedule(ch.id, e.target.value)}
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
        <Button variant="primary" fullWidth onClick={handleSubmit} disabled={isPending}>
          {isPending ? '⏳ Отправка...' : '📤 Отправить заявку'}
        </Button>
        <Button variant="secondary" fullWidth onClick={() => navigate(-1 as unknown as string)}>
          🔙 Назад
        </Button>
      </div>
    </ScreenShell>
  )
}
