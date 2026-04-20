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
    <div
      className={`flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3 sm:gap-5 mb-6 ${className}`}
    >
      <div className="min-w-0">
        <h1 className="font-display text-[22px] sm:text-[26px] font-bold tracking-[-0.02em] text-text-primary leading-[1.15] m-0 break-words">
          {title}
        </h1>
        {subtitle && (
          <p className="text-sm text-text-secondary mt-1.5">{subtitle}</p>
        )}
      </div>
      {action && <div className="flex flex-wrap gap-2 sm:flex-nowrap sm:flex-shrink-0">{action}</div>}
    </div>
  )
}
