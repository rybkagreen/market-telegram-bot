import type { ReactNode } from 'react'
import { Icon } from './Icon'

interface ScreenHeaderProps {
  title: string
  subtitle?: ReactNode
  crumbs?: string[]
  action?: ReactNode
  className?: string
}

export function ScreenHeader({
  title,
  subtitle,
  crumbs = [],
  action,
  className = '',
}: ScreenHeaderProps) {
  return (
    <div className={`flex items-end justify-between gap-5 mb-6 ${className}`}>
      <div className="min-w-0">
        {crumbs.length > 0 && (
          <div className="flex items-center gap-1.5 text-xs text-text-tertiary mb-2">
            {crumbs.map((c, i) => (
              <span key={i} className="flex items-center gap-1.5">
                <span className={i === crumbs.length - 1 ? 'text-text-secondary' : 'text-text-tertiary'}>
                  {c}
                </span>
                {i < crumbs.length - 1 && (
                  <Icon name="chevron-right" size={11} className="text-text-tertiary" />
                )}
              </span>
            ))}
          </div>
        )}
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
