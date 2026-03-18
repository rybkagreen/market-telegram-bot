import { useHaptic } from '@/hooks/useHaptic'
import styles from './MenuButton.module.css'

interface MenuButtonProps {
  icon: string
  iconBg?: string
  title: string
  subtitle?: string
  badge?: string | number
  variant?: 'default' | 'back'
  onClick: () => void
}

export function MenuButton({
  icon,
  iconBg = 'var(--rh-accent-muted)',
  title,
  subtitle,
  badge,
  variant = 'default',
  onClick,
}: MenuButtonProps) {
  const haptic = useHaptic()

  const handleClick = () => {
    haptic.tap()
    onClick()
  }

  return (
    <button
      type="button"
      className={`${styles.button} ${variant === 'back' ? styles.back : ''}`}
      onClick={handleClick}
    >
      <span className={styles.iconWrap} style={{ background: iconBg }}>
        {icon}
      </span>
      <span className={styles.content}>
        <span className={styles.title}>{title}</span>
        {subtitle && <span className={styles.subtitle}>{subtitle}</span>}
      </span>
      <span className={styles.right}>
        {badge !== undefined && <span className={styles.badge}>{badge}</span>}
        {variant !== 'back' && <span className={styles.chevron}>›</span>}
      </span>
    </button>
  )
}
