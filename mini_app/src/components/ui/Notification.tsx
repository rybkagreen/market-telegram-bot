import type { ReactNode } from 'react'
import styles from './Notification.module.css'

interface NotificationProps {
  type: 'info' | 'success' | 'warning' | 'danger'
  title?: string
  children: ReactNode
  icon?: string
}

const DEFAULT_ICONS: Record<NotificationProps['type'], string> = {
  info: 'ℹ️',
  success: '✅',
  warning: '⚠️',
  danger: '🚫',
}

export function Notification({ type, title, children, icon }: NotificationProps) {
  return (
    <div className={`${styles.box} ${styles[type]}`}>
      <span className={styles.icon}>{icon ?? DEFAULT_ICONS[type]}</span>
      <div className={styles.content}>
        {title && <div className={styles.title}>{title}</div>}
        <div className={styles.body}>{children}</div>
      </div>
    </div>
  )
}
