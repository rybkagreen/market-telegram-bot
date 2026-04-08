import { useHaptic } from '@/hooks/useHaptic'
import { StatusPill } from './StatusPill'
import styles from './ChannelCard.module.css'

interface ChannelCardProps {
  avatar?: string
  name: string
  username: string
  subscribers: string
  category?: string
  price?: string
  verified?: boolean
  status?: 'active' | 'inactive' | 'pending'
  onClick?: () => void
}

const STATUS_MAP = {
  active: 'success',
  inactive: 'neutral',
  pending: 'warning',
} as const

const STATUS_LABELS = {
  active: 'Активен',
  inactive: 'Неактивен',
  pending: 'Проверка',
}

export function ChannelCard({
  avatar,
  name,
  username,
  subscribers,
  category,
  price,
  verified = false,
  status,
  onClick,
}: ChannelCardProps) {
  const haptic = useHaptic()

  const handleClick = () => {
    if (!onClick) return
    haptic.tap()
    onClick()
  }

  return (
    <div
      className={`${styles.card} ${onClick ? styles.clickable : ''}`}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onClick={onClick ? handleClick : undefined}
      onKeyDown={onClick ? (e) => { if (e.key === 'Enter' || e.key === ' ') handleClick() } : undefined}
    >
      <div className={styles.avatar}>
        {avatar ? (
          <img src={avatar} alt={name} className={styles.avatarImg} />
        ) : (
          <span className={styles.avatarFallback}>{name.charAt(0).toUpperCase()}</span>
        )}
      </div>
      <div className={styles.info}>
        <div className={styles.nameRow}>
          <span className={styles.name}>{name}</span>
          {verified && <span className={styles.verified}>✓</span>}
          {status && (
            <StatusPill status={STATUS_MAP[status]} size="sm">
              {STATUS_LABELS[status]}
            </StatusPill>
          )}
        </div>
        <div className={styles.meta}>
          <span className={styles.username}>@{username}</span>
          {category && <span className={styles.dot}>·</span>}
          {category && <span className={styles.category}>{category}</span>}
        </div>
        <div className={styles.stats}>
          <span className={styles.stat}>👥 {subscribers}</span>
          {price && <span className={styles.price}>{price}</span>}
        </div>
      </div>
      {onClick && <span className={styles.chevron}>›</span>}
    </div>
  )
}
