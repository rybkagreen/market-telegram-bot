import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { StepIndicator, ArbitrationPanel, FeeBreakdown, Button, Notification } from '@shared/ui'
import { PUBLICATION_FORMATS, calcFormatPrice } from '@/lib/constants'
import { formatCurrency } from '@/lib/constants'
import { useCampaignWizardStore } from '@/stores/campaignWizardStore'
import { useCreatePlacement } from '@/hooks/useCampaignQueries'

export default function CampaignArbitration() {
  const navigate = useNavigate()
  const store = useCampaignWizardStore()
  const { mutateAsync: createPlacement, isPending } = useCreatePlacement()
  const [error, setError] = useState<string | null>(null)

  const format = store.format
  const formatInfo = format ? PUBLICATION_FORMATS[format] : null

  const tomorrow = new Date()
  tomorrow.setDate(tomorrow.getDate() + 1)
  const defaultDate = tomorrow.toISOString().substring(0, 10)

  const handleSubmit = async () => {
    if (!format || store.selectedChannels.length === 0) return
    setError(null)
    let firstId: number | null = null
    try {
      for (const ch of store.selectedChannels) {
        const schedule = store.proposedSchedules[ch.id] ?? `${defaultDate}T14:00`
        const basePrice = parseFloat(ch.settings.price_per_post)
        const ownerPrice = Math.round(calcFormatPrice(basePrice, format))
        const price = store.proposedPrices[ch.id] ?? ownerPrice
        // FIX: Append MSK timezone offset (+03:00) so backend stores correct time
        const result = await createPlacement({
          channel_id: ch.id,
          publication_format: format,
          ad_text: store.adText,
          proposed_price: price,
          proposed_schedule: `${schedule}:00+03:00`,
          is_test: store.isTest,
        })
        if (firstId === null) firstId = result.id
      }
      store.reset()
      navigate(`/adv/campaigns/${firstId}/waiting`)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Не удалось создать заявку'
      // Extract detail from HTTP error response if available
      let detail = message
      try {
        const body = JSON.parse(message)
        if (body.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
      } catch { /* not JSON */ }
      setError(detail)
    }
  }

  const feeRows = store.selectedChannels.map((ch) => ({
    label: `@${ch.username}`,
    value: formatCurrency(store.proposedPrices[ch.id] ?? 0),
  }))

  return (
    <div className="space-y-6">
      <StepIndicator total={6} current={5} labels={['Тематика', 'Каналы', 'Формат', 'Текст', 'Условия', 'Оплата']} />

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
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-text-secondary">💰 Цена владельца</span>
                <span className="text-sm font-medium text-text-primary">{formatCurrency(ownerPrice)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-text-secondary">💬 Ваше предложение</span>
                <input
                  type="number"
                  className="w-32 px-3 py-1.5 bg-harbor-elevated border border-border rounded-md text-sm text-text-primary text-right focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/30"
                  value={currentProposed}
                  onChange={(e) =>
                    store.setProposedPrice(ch.id, parseInt(e.target.value, 10) || 0)
                  }
                />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-text-secondary">📅 Дата публикации</span>
                <input
                  type="date"
                  className="px-3 py-1.5 bg-harbor-elevated border border-border rounded-md text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/30"
                  value={currentDatePart ?? defaultDate}
                  min={defaultDate}
                  onChange={(e) =>
                    store.setProposedSchedule(ch.id, `${e.target.value}T${currentTimePart ?? '14:00'}`)
                  }
                />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-text-secondary">🕐 Время публикации</span>
                <input
                  type="time"
                  className="px-3 py-1.5 bg-harbor-elevated border border-border rounded-md text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/30"
                  value={currentTimePart ?? '14:00'}
                  onChange={(e) =>
                    store.setProposedSchedule(ch.id, `${currentDatePart ?? defaultDate}T${e.target.value}`)
                  }
                />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-text-secondary">📈 Частота</span>
                <span className="text-sm font-medium text-text-primary">1 пост</span>
              </div>
            </div>
          </ArbitrationPanel>
        )
      })}

      {store.selectedChannels.length === 0 && (
        <p className="text-text-tertiary text-center py-4">Нет выбранных каналов</p>
      )}

      {feeRows.length > 0 && (
        <FeeBreakdown
          rows={feeRows}
          total={{ label: 'Итого к оплате', value: formatCurrency(store.getTotalPrice()) }}
        />
      )}

      {error && (
        <Notification type="danger">
          <span className="text-sm">❌ {error}</span>
        </Notification>
      )}

      <div className="flex flex-col gap-3">
        <Button variant="primary" fullWidth onClick={() => void handleSubmit()} loading={isPending}>
          {isPending ? '⏳ Отправка...' : '📤 Отправить заявку'}
        </Button>
        <Button variant="secondary" fullWidth onClick={() => navigate(-1 as unknown as string)}>
          🔙 Назад
        </Button>
      </div>
    </div>
  )
}
