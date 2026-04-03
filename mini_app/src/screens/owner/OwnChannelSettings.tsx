import React, { useState } from 'react'
import { useParams } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Card, Button, Toggle, Skeleton, Notification, Text } from '@/components/ui'
import { PUBLICATION_FORMATS, MIN_PRICE_PER_POST } from '@/lib/constants'
import { formatCurrency, calcFormatPrice } from '@/lib/formatters'
import { useMyChannels, useChannelSettings, useUpdateChannelSettings } from '@/hooks/queries/useChannelQueries'
import type { PublicationFormat, ChannelSettings } from '@/lib/types'
import { useHaptic } from '@/hooks/useHaptic'
import styles from './OwnChannelSettings.module.css'

const FORMAT_KEYS: PublicationFormat[] = ['post_24h', 'post_48h', 'post_7d', 'pin_24h', 'pin_48h']

type FormatState = {
  post_24h: boolean
  post_48h: boolean
  post_7d: boolean
  pin_24h: boolean
  pin_48h: boolean
}

const FORMAT_SETTING_KEY: Record<PublicationFormat, keyof FormatState> = {
  post_24h: 'post_24h',
  post_48h: 'post_48h',
  post_7d: 'post_7d',
  pin_24h: 'pin_24h',
  pin_48h: 'pin_48h',
}

function getFormatState(s: ChannelSettings): FormatState {
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
  const haptic = useHaptic()

  const numericId = id ? parseInt(id) : null

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

  // Initialize form from settings
  const initializedSettings = React.useRef(false)
  
  React.useEffect(() => {
    if (settings && !initializedSettings.current) {
      initializedSettings.current = true
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

  const priceNum = parseFloat(price) || 0
  const isPriceValid = priceNum >= MIN_PRICE_PER_POST
  const isMaxDayValid = parseInt(maxPerDay) <= 5

  const handleSave = () => {
    if (!isPriceValid) {
      alert(`Минимальная цена: ${MIN_PRICE_PER_POST} ₽`)
      return
    }
    if (!isMaxDayValid) {
      alert('Максимум 5 постов в день')
      return
    }
    if (!numericId) return
    haptic.success()
    updateMutation.mutate({
      id: numericId,
      data: {
        price_per_post: price,
        allow_format_post_24h: formats.post_24h,
        allow_format_post_48h: formats.post_48h,
        allow_format_post_7d: formats.post_7d,
        allow_format_pin_24h: formats.pin_24h,
        allow_format_pin_48h: formats.pin_48h,
        publish_start_time: publishStart,
        publish_end_time: publishEnd,
        break_start_time: breakStart || null,
        break_end_time: breakEnd || null,
        max_posts_per_day: parseInt(maxPerDay),
        auto_accept_enabled: autoAccept,
      },
    })
  }

  const toggleFormat = (key: PublicationFormat) => {
    setFormats((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  const isPinFormat = (key: PublicationFormat) => key.startsWith('pin_')

  if (isLoading) {
    return (
      <ScreenShell>
        <Skeleton height={120} radius="lg" />
        <Skeleton height={200} radius="lg" />
        <Skeleton height={180} radius="lg" />
      </ScreenShell>
    )
  }

  if (isError || !settings) {
    return (
      <ScreenShell>
        <Notification type="danger">
          <Text variant="sm">❌ Не удалось загрузить настройки канала</Text>
        </Notification>
      </ScreenShell>
    )
  }

  return (
    <ScreenShell>
      <p className={styles.sectionTitle}>⚙️ Настройки @{channel?.username ?? id}</p>

      <Card title="Базовая цена за пост">
        <label className={styles.label}>Цена (мин. 1 000 ₽)</label>
        <input
          className={`${styles.input} ${!isPriceValid && price !== '' ? styles.inputError : ''}`}
          type="number"
          min={MIN_PRICE_PER_POST}
          value={price}
          onChange={(e) => setPrice(e.target.value)}
        />
        <p className={styles.hint}>Реальная стоимость умножается на коэфф. формата</p>
      </Card>

      <Card title="Разрешённые форматы">
        {FORMAT_KEYS.map((key) => {
          const fmt = PUBLICATION_FORMATS[key]
          const fmtPrice = calcFormatPrice(priceNum, key)
          const isPin = isPinFormat(key)
          return (
            <div key={key} className={styles.formatRow}>
              <div className={styles.formatInfo}>
                <span className={styles.formatLabel}>
                  {fmt.icon} {fmt.name} (×{fmt.multiplier}) · {formatCurrency(fmtPrice)}
                </span>
                {isPin && (
                  <span className={styles.formatWarning}>⚠️ Требует права закреплять</span>
                )}
              </div>
              <Toggle
                checked={formats[FORMAT_SETTING_KEY[key]]}
                onChange={() => toggleFormat(key)}
              />
            </div>
          )
        })}
      </Card>

      <Card title="Расписание публикаций">
        <div className={styles.timeRow}>
          <span className={styles.timeLabel}>Начало</span>
          <input
            className={styles.timeInput}
            type="time"
            value={publishStart}
            onChange={(e) => setPublishStart(e.target.value)}
          />
        </div>
        <div className={styles.timeRow}>
          <span className={styles.timeLabel}>Конец</span>
          <input
            className={styles.timeInput}
            type="time"
            value={publishEnd}
            onChange={(e) => setPublishEnd(e.target.value)}
          />
        </div>
        <div className={styles.timeRow}>
          <span className={styles.timeLabel}>Перерыв — начало</span>
          <input
            className={styles.timeInput}
            type="time"
            value={breakStart}
            onChange={(e) => setBreakStart(e.target.value)}
          />
        </div>
        <div className={styles.timeRow}>
          <span className={styles.timeLabel}>Перерыв — конец</span>
          <input
            className={styles.timeInput}
            type="time"
            value={breakEnd}
            onChange={(e) => setBreakEnd(e.target.value)}
          />
        </div>
        <div className={styles.timeRow}>
          <span className={styles.timeLabel}>Макс. постов в день</span>
          <input
            className={`${styles.timeInput} ${!isMaxDayValid && maxPerDay !== '' ? styles.inputError : ''}`}
            type="number"
            min={1}
            max={5}
            value={maxPerDay}
            onChange={(e) => setMaxPerDay(e.target.value)}
          />
        </div>
      </Card>

      <Card>
        <Toggle
          checked={autoAccept}
          onChange={setAutoAccept}
          label="Автоподтверждение заявок"
        />
      </Card>

      <Button fullWidth onClick={handleSave} disabled={updateMutation.isPending}>
        {updateMutation.isPending ? '⏳ Сохранение...' : '💾 Сохранить настройки'}
      </Button>
    </ScreenShell>
  )
}
