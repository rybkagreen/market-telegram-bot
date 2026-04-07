interface NotificationProps {
  type?: 'info' | 'success' | 'warning' | 'danger'
  children: React.ReactNode
  className?: string
}

const typeClasses: Record<string, string> = {
  info: 'bg-info-muted border-info text-text-primary',
  success: 'bg-success-muted border-success text-text-primary',
  warning: 'bg-warning-muted border-warning text-text-primary',
  danger: 'bg-danger-muted border-danger text-text-primary',
}

export function Notification({ type = 'info', children, className = '' }: NotificationProps) {
  return (
    <div className={`px-4 py-3 rounded-md border ${typeClasses[type]} ${className}`}>
      <div className="flex items-start gap-3">
        <span className="mt-0.5 text-sm">{children}</span>
      </div>
    </div>
  )
}
