import styles from './TestModeBadge.module.css'

interface TestModeBadgeProps {
  label?: string
}

/**
 * Badge component for displaying test mode indicator.
 * Shows "ТЕСТ" by default or custom label.
 */
export function TestModeBadge({ label = 'ТЕСТ' }: TestModeBadgeProps) {
  return (
    <span className={styles.badge} title="Тестовый режим">
      {label}
    </span>
  )
}
