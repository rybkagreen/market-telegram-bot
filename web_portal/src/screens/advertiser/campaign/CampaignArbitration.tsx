import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FeeBreakdown, Button, Notification, Icon } from '@shared/ui'
import { PUBLICATION_FORMATS, calcFormatPrice } from '@/lib/constants'
import { formatCurrency } from '@/lib/constants'
import { useCampaignWizardStore } from '@/stores/campaignWizardStore'
import { useCreatePlacement } from '@/hooks/useCampaignQueries'
import { CampaignWizardShell } from './_shell'

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
      let detail = message
      try {
        const body = JSON.parse(message)
        if (body.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
      } catch {
        /* not JSON */
      }
      setError(detail)
    }
  }

  const feeRows = store.selectedChannels.map((ch) => ({
    label: `@${ch.username}`,
    value: formatCurrency(store.proposedPrices[ch.id] ?? 0),
  }))

  return (
    <CampaignWizardShell
      step={5}
      title="Условия размещения"
      subtitle={`Формат: ${formatInfo?.name ?? '—'} · каналов: ${store.selectedChannels.length}`}
      footer={
        <>
          <Button
            variant="secondary"
            iconLeft="arrow-left"
            onClick={() => navigate('/adv/campaigns/new/text')}
          >
            Назад
          </Button>
          <div className="flex-1 hidden sm:flex items-center justify-center gap-2 text-[12.5px] text-text-tertiary">
            <Icon name="ruble" size={13} />
            Итого: {formatCurrency(store.getTotalPrice())}
          </div>
          <Button
            variant="primary"
            iconRight="arrow-right"
            loading={isPending}
            onClick={() => void handleSubmit()}
          >
            Отправить заявку
          </Button>
        </>
      }
    >
      {store.selectedChannels.length === 0 ? (
        <div className="bg-harbor-card border border-dashed border-border rounded-xl p-10 text-center">
          <div className="inline-grid place-items-center w-12 h-12 rounded-[12px] bg-harbor-elevated text-text-tertiary mb-3">
            <Icon name="channels" size={20} />
          </div>
          <div className="font-display text-base font-semibold text-text-primary mb-1">
            Нет выбранных каналов
          </div>
          <div className="text-[13px] text-text-secondary mb-4">
            Вернитесь на шаг «Каналы» и выберите хотя бы один.
          </div>
          <Button
            variant="secondary"
            iconLeft="arrow-left"
            onClick={() => navigate('/adv/campaigns/new/channels')}
          >
            К выбору каналов
          </Button>
        </div>
      ) : (
        <>
          <div className="space-y-3">
            {store.selectedChannels.map((ch) => {
              const basePrice = parseFloat(ch.settings.price_per_post)
              const ownerPrice = format ? calcFormatPrice(basePrice, format) : basePrice
              const currentProposed = store.proposedPrices[ch.id] ?? ownerPrice
              const currentSchedule = store.proposedSchedules[ch.id] ?? `${defaultDate}T14:00`
              const currentDateTime = currentSchedule.includes('T')
                ? currentSchedule
                : `${defaultDate}T${currentSchedule}`
              const [currentDatePart, currentTimePart] = currentDateTime.split('T')

              return (
                <div
                  key={ch.id}
                  className="bg-harbor-card border border-border rounded-xl overflow-hidden"
                >
                  <div className="flex items-center justify-between px-5 py-3 border-b border-border bg-harbor-secondary">
                    <div className="flex items-center gap-2">
                      <Icon name="channels" size={14} className="text-text-tertiary" />
                      <span className="font-display text-[13.5px] font-semibold text-text-primary">
                        @{ch.username}
                      </span>
                    </div>
                    <span className="text-[11px] text-text-tertiary uppercase tracking-[0.08em] font-semibold">
                      {formatInfo?.name ?? format}
                    </span>
                  </div>

                  <div className="px-5 py-4 grid gap-3 sm:grid-cols-2">
                    <ArbRow label="Цена владельца" icon="ruble">
                      <span className="text-sm font-mono tabular-nums text-text-secondary">
                        {formatCurrency(ownerPrice)}
                      </span>
                    </ArbRow>
                    <ArbRow label="Ваше предложение" icon="edit">
                      <input
                        type="number"
                        className="w-28 px-3 py-1.5 bg-harbor-elevated border border-border rounded-md text-sm font-mono tabular-nums text-text-primary text-right focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/30"
                        value={currentProposed}
                        onChange={(e) =>
                          store.setProposedPrice(ch.id, parseInt(e.target.value, 10) || 0)
                        }
                      />
                    </ArbRow>
                    <ArbRow label="Дата публикации" icon="calendar">
                      <input
                        type="date"
                        className="px-3 py-1.5 bg-harbor-elevated border border-border rounded-md text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/30"
                        value={currentDatePart ?? defaultDate}
                        min={defaultDate}
                        onChange={(e) =>
                          store.setProposedSchedule(
                            ch.id,
                            `${e.target.value}T${currentTimePart ?? '14:00'}`,
                          )
                        }
                      />
                    </ArbRow>
                    <ArbRow label="Время" icon="clock">
                      <input
                        type="time"
                        className="px-3 py-1.5 bg-harbor-elevated border border-border rounded-md text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/30"
                        value={currentTimePart ?? '14:00'}
                        onChange={(e) =>
                          store.setProposedSchedule(
                            ch.id,
                            `${currentDatePart ?? defaultDate}T${e.target.value}`,
                          )
                        }
                      />
                    </ArbRow>
                  </div>
                </div>
              )
            })}
          </div>

          {feeRows.length > 0 && (
            <FeeBreakdown
              rows={feeRows}
              total={{ label: 'Итого к оплате', value: formatCurrency(store.getTotalPrice()) }}
            />
          )}

          {error && <Notification type="danger">{error}</Notification>}
        </>
      )}
    </CampaignWizardShell>
  )
}

function ArbRow({
  label,
  icon,
  children,
}: {
  label: string
  icon: 'ruble' | 'edit' | 'calendar' | 'clock'
  children: React.ReactNode
}) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="flex items-center gap-2 text-[13px] text-text-secondary">
        <Icon name={icon} size={13} className="text-text-tertiary" />
        {label}
      </span>
      {children}
    </div>
  )
}
