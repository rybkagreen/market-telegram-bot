import type { ReactNode } from 'react'

interface ScreenHeaderProps {
  title: string
  subtitle?: ReactNode
  action?: ReactNode
  className?: string
}

export function ScreenHeader({
  title,
  subtitle,
  action,
  className = '',
}: ScreenHeaderProps) {
  return (
    <div className={`flex items-end justify-between gap-5 mb-6 ${className}`}>
      <div className="min-w-0">
        <h1 className="font-display text-[26px] font-bold tracking-[-0.02em] text-text-primary leading-[1.15] m-0">
          {title}
        </h1>
        {subtitle && (
          <p className="text-sm text-text-secondary mt-1.5">{subtitle}</p>
        )}
      </div>
      {action && <div className="flex-shrink-0">{action}</div>}
    </div>
  )
}
