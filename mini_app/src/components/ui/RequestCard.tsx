import { useHaptic } from '@/hooks/useHaptic'
import { StatusPill } from './StatusPill'
import styles from './RequestCard.module.css'

type RequestStatus =
  | 'pending_owner'
  | 'counter_offer'
  | 'pending_payment'
  | 'escrow'
  | 'published'
  | 'cancelled'
  | 'refunded'
  | 'failed'

interface RequestCardProps {
  id: number
  channelName: string
  adText: string
  price: string
  date: string
  status: RequestStatus
  isOwner?: boolean
  onClick?: () => void
}

const STATUS_PILL: Record<RequestStatus, { variant: 'success' | 'warning' | 'danger' | 'info' | 'purple' | 'neutral'; label: string }> = {
  pending_owner:   { variant: 'warning', label: 'Ожидает' },
  counter_offer:   { variant: 'purple',  label: 'Встречное' },
  pending_payment: { variant: 'warning', label: 'Оплата' },
  escrow:          { variant: 'info',    label: 'Эскроу' },
  published:       { variant: 'success', label: 'Опубликовано' },
  cancelled:       { variant: 'neutral', label: 'Отменено' },
  refunded:        { variant: 'neutral', label: 'Возврат' },
  failed:          { variant: 'danger',  label: 'Ошибка' },
}

export function RequestCard({
  id,
  channelName,
  adText,
  price,
  date,
  status,
  isOwner = false,
  onClick,
}: RequestCardProps) {
  const haptic = useHaptic()
  const pill = STATUS_PILL[status]

  const handleClick = () => {
    if (!onClick) return
    haptic.tap()
    onClick()
  }

  return (
    <div
      className={`${styles.card} ${onClick ? styles.clickable : ''}`}
      onClick={onClick ? handleClick : undefined}
    >
      <div className={styles.header}>
        <span className={styles.channel}>{channelName}</span>
        <StatusPill status={pill.variant} size="sm">{pill.label}</StatusPill>
      </div>
      <div className={styles.text}>{adText}</div>
      <div className={styles.footer}>
        <span className={styles.meta}>
          {isOwner ? '📢' : '🎯'} #{id} · {date}
        </span>
        <span className={styles.price}>{price}</span>
      </div>
    </div>
  )
}
