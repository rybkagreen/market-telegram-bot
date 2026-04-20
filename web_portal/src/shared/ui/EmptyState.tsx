import type { ReactNode } from 'react'
import { Button } from './Button'
import { Icon } from './Icon'
import type { IconName } from './icon-names'

interface EmptyStateProps {
  icon?: IconName
  title: string
  description?: string
  action?: { label: string; onClick: () => void }
  children?: ReactNode
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  children,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      {icon && (
        <div className="w-14 h-14 rounded-[14px] bg-harbor-elevated text-text-tertiary grid place-items-center mb-4">
          <Icon name={icon} size={28} />
        </div>
      )}
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
