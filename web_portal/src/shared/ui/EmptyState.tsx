import type { ReactNode } from 'react'
import { Button } from './Button'

interface EmptyStateProps {
  icon?: string
  title: string
  description?: string
  action?: { label: string; onClick: () => void }
  children?: ReactNode
}

export function EmptyState({ icon = '🌊', title, description, action, children }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div className="text-5xl mb-4">{icon}</div>
      <div className="text-lg font-semibold text-text-primary mb-1">{title}</div>
      {description && <div className="text-sm text-text-secondary mb-4">{description}</div>}
      {children}
      {action && (
        <Button variant="secondary" size="md" onClick={action.onClick}>
          {action.label}
        </Button>
      )}
    </div>
  )
}
