import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Button,
  Toggle,
  Input,
  Skeleton,
  Notification,
  Icon,
  ScreenHeader,
} from '@shared/ui'
import { PUBLICATION_FORMATS, calcFormatPrice, MIN_PRICE_PER_POST } from '@/lib/constants'
import { formatCurrency } from '@/lib/constants'
import { useMyChannels } from '@/hooks/useChannelQueries'
import { useChannelSettings, useUpdateChannelSettings } from '@/hooks/useChannelSettings'
import type { PublicationFormat } from '@/stores/campaignWizardStore'

const FORMAT_KEYS = ['post_24h', 'post_48h', 'post_7d', 'pin_24h', 'pin_48h'] as PublicationFormat[]

type FormatState = {
  post_24h: boolean
  post_48h: boolean
  post_7d: boolean
  pin_24h: boolean
  pin_48h: boolean
}

function getFormatState(s: NonNullable<ReturnType<typeof useChannelSettings>['data']>): FormatState {
  return {
    post_24h: s.allow_format_post_24h,
    post_48h: s.allow_format_post_48h,
    post_7d: s.allow_format_post_7d,
    pin_24h: s.allow_format_pin_24h,
    pin_48h: s.allow_format_pin_48h,
  }
}

export default function OwnChannelSettings() {
  const { id } = useParams()
  const navigate = useNavigate()
  const numericId = id ? parseInt(id, 10) : null

  const { data: channels } = useMyChannels()
  const { data: settings, isLoading, isError } = useChannelSettings(numericId)
  const updateMutation = useUpdateChannelSettings()

  const channel = channels?.find((c) => c.id === numericId) ?? null

  const [price, setPrice] = useState('')
  const [formats, setFormats] = useState<FormatState>({
    post_24h: true,
    post_48h: true,
    post_7d: true,
    pin_24h: false,
    pin_48h: false,
  })
  const [publishStart, setPublishStart] = useState('09:00')
  const [publishEnd, setPublishEnd] = useState('21:00')
  const [breakStart, setBreakStart] = useState('')
  const [breakEnd, setBreakEnd] = useState('')
  const [maxPerDay, setMaxPerDay] = useState('3')
  const [autoAccept, setAutoAccept] = useState(false)

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (settings) {
      setPrice(settings.price_per_post)
      setFormats(getFormatState(settings))
      setPublishStart(settings.publish_start_time ?? '09:00')
      setPublishEnd(settings.publish_end_time ?? '21:00')
      setBreakStart(settings.break_start_time ?? '')
      setBreakEnd(settings.break_end_time ?? '')
      setMaxPerDay(String(settings.max_posts_per_day))
      setAutoAccept(settings.auto_accept_enabled)
    }
  }, [settings])
  /* eslint-enable react-hooks/set-state-in-effect */

  const priceNum = parseFloat(price) || 0
  const isPriceValid = priceNum >= MIN_PRICE_PER_POST || price === ''
  const isMaxDayValid = parseInt(maxPerDay) <= 5 || maxPerDay === ''

  const handleSave = () => {
    if (!isPriceValid) return
    if (!isMaxDayValid) return
    if (!numericId) return
    updateMutation.mutate(
      {
        id: numericId,
        data: {
          price_per_post: parseInt(price, 10),
          allow_format_post_24h: formats.post_24h,
          allow_format_post_48h: formats.post_48h,
          allow_format_post_7d: formats.post_7d,
          allow_format_pin_24h: formats.pin_24h,
          allow_format_pin_48h: formats.pin_48h,
          publish_start_time: publishStart,
          publish_end_time: publishEnd,
          break_start_time: breakStart || null,
          break_end_time: breakEnd || null,
          max_posts_per_day: parseInt(maxPerDay, 10),
          auto_accept_enabled: autoAccept,
        },
      },
      {
        onSuccess: () => navigate('/own/channels'),
        onError: (error) => {
          console.error('Failed to save settings:', error)
          alert('Не удалось сохранить настройки. Проверьте введённые данные.')
        },
      },
    )
  }

  if (isLoading) {
    return (
      <div className="max-w-[1080px] mx-auto space-y-4">
        <Skeleton className="h-20" />
        <Skeleton className="h-64" />
        <Skeleton className="h-40" />
      </div>
    )
  }

  if (isError || !settings) {
    return (
      <div className="max-w-[1080px] mx-auto">
        <Notification type="danger">Не удалось загрузить настройки канала</Notification>
      </div>
    )
  }

  const channelTitle = channel?.title ?? `Канал #${numericId}`
  const channelUsername = channel?.username ?? ''

  return (
    <div className="max-w-[1080px] mx-auto">
      <ScreenHeader
        crumbs={['Главная', 'Владелец', 'Каналы', `@${channelUsername}`, 'Настройки']}
        title="Настройки канала"
        subtitle={channel ? `${channelTitle} · @${channelUsername}` : 'Параметры публикаций и расписания'}
        action={
          <Button
            variant="secondary"
            iconLeft="arrow-left"
            onClick={() => navigate('/own/channels')}
          >
            К списку
          </Button>
        }
      />

      <div className="space-y-4">
        <SectionCard icon="ruble" title="Базовая цена за пост">
          <Input
            label="Цена за публикацию"
            type="number"
            min={MIN_PRICE_PER_POST}
            value={price}
            onChange={setPrice}
            hint={`Минимум ${formatCurrency(MIN_PRICE_PER_POST)}. Реальная стоимость умножается на коэффициент формата.`}
            invalid={!isPriceValid && price !== ''}
          />
        </SectionCard>

        <SectionCard icon="docs" title="Разрешённые форматы">
          <div className="space-y-1 divide-y divide-border">
            {FORMAT_KEYS.map((key) => {
              const fmt = PUBLICATION_FORMATS[key]
              const fmtPrice = calcFormatPrice(priceNum, key)
              const isPin = key.startsWith('pin_')
              return (
                <div key={key} className="flex items-center justify-between py-3 first:pt-0 last:pb-0">
                  <div className="flex-1">
                    <div className="text-[13.5px] font-semibold text-text-primary">
                      {fmt.name}{' '}
                      <span className="text-text-tertiary font-mono tabular-nums">
                        × {fmt.multiplier}
                      </span>
                    </div>
                    <div className="text-[13px] text-text-secondary font-mono tabular-nums">
                      {formatCurrency(fmtPrice)}
                    </div>
                    {isPin && (
                      <div className="text-[11.5px] text-warning mt-0.5 flex items-center gap-1.5">
                        <Icon name="warning" size={12} />
                        Требуются права на закрепление в канале
                      </div>
                    )}
                  </div>
                  <Toggle
                    checked={formats[key]}
                    onChange={() => setFormats((prev) => ({ ...prev, [key]: !prev[key] }))}
                  />
                </div>
              )
            })}
          </div>
        </SectionCard>

        <SectionCard icon="clock" title="Расписание публикаций">
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="Начало окна"
                type="time"
                value={publishStart}
                onChange={setPublishStart}
              />
              <Input
                label="Конец окна"
                type="time"
                value={publishEnd}
                onChange={setPublishEnd}
              />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="Перерыв — начало"
                type="time"
                value={breakStart}
                onChange={setBreakStart}
              />
              <Input
                label="Перерыв — конец"
                type="time"
                value={breakEnd}
                onChange={setBreakEnd}
              />
            </div>
            <Input
              label="Макс. постов в день"
              type="number"
              min={1}
              max={5}
              value={maxPerDay}
              onChange={setMaxPerDay}
              hint="От 1 до 5 публикаций в сутки"
              invalid={!isMaxDayValid && maxPerDay !== ''}
            />
          </div>
        </SectionCard>

        <SectionCard icon="zap" title="Автоподтверждение">
          <Toggle
            checked={autoAccept}
            onChange={setAutoAccept}
            label="Автоматически принимать заявки по базовой цене"
          />
          <p className="text-[12px] text-text-tertiary mt-2">
            Заявки с предложенной ценой ≥ базовой будут приняты без вашего участия.
          </p>
        </SectionCard>

        <div className="flex flex-col sm:flex-row gap-3">
          <Button
            variant="primary"
            iconLeft="check"
            className="flex-1"
            loading={updateMutation.isPending}
            onClick={handleSave}
          >
            Сохранить настройки
          </Button>
          <Button
            variant="secondary"
            iconLeft="arrow-left"
            onClick={() => navigate('/own/channels')}
          >
            Отмена
          </Button>
        </div>
      </div>
    </div>
  )
}

function SectionCard({
  icon,
  title,
  children,
}: {
  icon: 'ruble' | 'docs' | 'clock' | 'zap'
  title: string
  children: React.ReactNode
}) {
  return (
    <div className="bg-harbor-card border border-border rounded-xl overflow-hidden">
      <div className="px-5 py-3 border-b border-border flex items-center gap-2">
        <Icon name={icon} size={14} className="text-text-tertiary" />
        <span className="font-display text-[14px] font-semibold text-text-primary">{title}</span>
      </div>
      <div className="p-5">{children}</div>
    </div>
  )
}
