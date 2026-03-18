import styles from './StatusPill.module.css'

interface StatusPillProps {
  status: 'success' | 'warning' | 'danger' | 'info' | 'purple' | 'neutral'
  children: React.ReactNode
  size?: 'sm' | 'md'
}

export function StatusPill({ status, children, size = 'md' }: StatusPillProps) {
  return (
    <span className={`${styles.pill} ${styles[status]} ${styles[size]}`}>
      {children}
    </span>
  )
}
