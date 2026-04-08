import { useHaptic } from '@/hooks/useHaptic'
import styles from './Card.module.css'

interface CardProps {
  title?: string
  children: React.ReactNode
  onClick?: () => void
  glass?: boolean
  className?: string
}

export function Card({ title, children, onClick, glass = false, className }: CardProps) {
  const haptic = useHaptic()

  const handleClick = () => {
    if (!onClick) return
    haptic.tap()
    onClick()
  }

  const cn = [
    styles.card,
    glass ? styles.glass : '',
    onClick ? styles.clickable : '',
    className ?? '',
  ].filter(Boolean).join(' ')

  return (
    <div className={cn} role={onClick ? 'button' : undefined} tabIndex={onClick ? 0 : undefined} onClick={onClick ? handleClick : undefined} onKeyDown={onClick ? (e) => { if (e.key === 'Enter' || e.key === ' ') handleClick() } : undefined}>
      {title && <p className={styles.title}>{title}</p>}
      {children}
    </div>
  )
}
