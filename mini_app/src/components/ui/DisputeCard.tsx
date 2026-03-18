import { useHaptic } from '@/hooks/useHaptic'
import { StatusPill } from './StatusPill'
import styles from './DisputeCard.module.css'

type DisputeStatus = 'open' | 'in_review' | 'resolved' | 'closed'

interface DisputeCardProps {
  id: number
  title: string
  description: string
  status: DisputeStatus
  createdAt: string
  amount?: string
  onClick?: () => void
}

const STATUS_PILL: Record<DisputeStatus, { variant: 'success' | 'warning' | 'danger' | 'info' | 'purple' | 'neutral'; label: string }> = {
  open:      { variant: 'danger',  label: 'Открыт' },
  in_review: { variant: 'warning', label: 'На рассмотрении' },
  resolved:  { variant: 'success', label: 'Решён' },
  closed:    { variant: 'neutral', label: 'Закрыт' },
}

export function DisputeCard({
  id,
  title,
  description,
  status,
  createdAt,
  amount,
  onClick,
}: DisputeCardProps) {
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
        <span className={styles.id}>Спор #{id}</span>
        <StatusPill status={pill.variant} size="sm">{pill.label}</StatusPill>
      </div>
      <div className={styles.title}>{title}</div>
      <div className={styles.description}>{description}</div>
      <div className={styles.footer}>
        <span className={styles.date}>{createdAt}</span>
        {amount && <span className={styles.amount}>{amount}</span>}
      </div>
    </div>
  )
}
