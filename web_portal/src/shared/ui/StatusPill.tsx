import type { ReactNode } from 'react'

interface StatusPillProps {
  status: 'success' | 'warning' | 'danger' | 'default' | 'info' | 'neutral'
  size?: 'sm' | 'md'
  children: ReactNode
  className?: string
}

const statusClasses: Record<string, string> = {
  success: 'bg-success-muted text-success border-success-muted',
  warning: 'bg-warning-muted text-warning border-warning-muted',
  danger: 'bg-danger-muted text-danger border-danger-muted',
  default: 'bg-harbor-elevated text-text-secondary border-border',
  info: 'bg-harbor-elevated text-text-secondary border-border',
  neutral: 'bg-harbor-elevated text-text-tertiary border-border',
}

const sizeClasses: Record<string, string> = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-3 py-1 text-sm',
}

export function StatusPill({ status = 'default', size = 'md', children, className = '' }: StatusPillProps) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border font-medium ${statusClasses[status]} ${sizeClasses[size]} ${className}`}>
      {children}
    </span>
  )
}
