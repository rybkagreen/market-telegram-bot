import type { ReactNode } from 'react'
import { Button } from './Button'
import styles from './ArbitrationPanel.module.css'

interface ArbitrationAction {
  label: string
  variant: 'primary' | 'secondary' | 'danger' | 'success'
  onClick: () => void
  loading?: boolean
}

interface ArbitrationPanelProps {
  title: string
  description?: string
  status?: string
  actions?: ArbitrationAction[]
  children?: ReactNode
}

export function ArbitrationPanel({
  title,
  description,
  status,
  actions = [],
  children,
}: ArbitrationPanelProps) {
  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <span className={styles.badge}>⚖️</span>
        <div className={styles.info}>
          <div className={styles.title}>{title}</div>
          {status && <div className={styles.status}>{status}</div>}
        </div>
      </div>
      {description && <p className={styles.description}>{description}</p>}
      {children && <div className={styles.content}>{children}</div>}
      {actions.length > 0 && (
        <div className={styles.actions}>
          {actions.map((action, i) => (
            <Button
              key={i}
              variant={action.variant}
              size="sm"
              loading={action.loading}
              onClick={action.onClick}
              fullWidth
            >
              {action.label}
            </Button>
          ))}
        </div>
      )}
    </div>
  )
}
