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
      {/* ─── HEADER: Avatar + Title + Status ─── */}
      <div className={styles.header}>
        <div className={styles.avatar}>
          {avatar ? (
            <img src={avatar} alt={name} className={styles.avatarImg} />
          ) : (
            <span className={styles.avatarFallback}>{name.charAt(0).toUpperCase()}</span>
          )}
        </div>

        <div className={styles.titleBlock}>
          <div className={styles.nameRow}>
            <span className={styles.name}>{name}</span>
            {verified && <span className={styles.verified}>✓</span>}
          </div>
          <span className={styles.username}>@{username}</span>
        </div>

        {status && (
          <StatusPill status={STATUS_MAP[status]} size="sm">
            {STATUS_LABELS[status]}
          </StatusPill>
        )}
      </div>

      {/* ─── BODY: Stats ─── */}
      <div className={styles.stats}>
        <div className={styles.statItem}>
          <span className={styles.statValue}>{subscribers}</span>
          <span className={styles.statLabel}>подписчиков</span>
        </div>

        {category && (
          <div className={styles.statItem}>
            <span className={styles.statValue}>{category}</span>
            <span className={styles.statLabel}>категория</span>
          </div>
        )}

        {price && (
          <div className={styles.statItem}>
            <span className={styles.statValue}>{price}</span>
            <span className={styles.statLabel}>за пост</span>
          </div>
        )}
      </div>

      {/* ─── FOOTER: Action hint ─── */}
      {onClick && (
        <div className={styles.footer}>
          <span className={styles.chevron} aria-hidden="true">›</span>
        </div>
      )}
    </div>
  )
}
