import type { ReactNode } from 'react'

/* ============================================================
   MobileDataCard — stacked replacement for table-like rows on <md
   Generic (not channel/campaign-specific like MobileCard).
   Use for: history lists (transactions, payouts, acts, reputation)
   where a desktop grid collapses into a single card on mobile.
   ============================================================ */

interface MobileDataCardRow {
  label: string
  value: ReactNode
  emphasis?: 'default' | 'success' | 'danger' | 'warning'
}

interface MobileDataCardProps {
  leadingIcon?: ReactNode
  title: ReactNode
  subtitle?: ReactNode
  trailing?: ReactNode
  rows?: MobileDataCardRow[]
  footer?: ReactNode
  onClick?: () => void
  className?: string
}

const emphasisClasses: Record<NonNullable<MobileDataCardRow['emphasis']>, string> = {
  default: 'text-text-primary',
  success: 'text-success',
  danger: 'text-danger',
  warning: 'text-warning',
}

export function MobileDataCard({
  leadingIcon,
  title,
  subtitle,
  trailing,
  rows = [],
  footer,
  onClick,
  className = '',
}: MobileDataCardProps) {
  const clickable = !!onClick
  const Container = clickable ? 'button' : 'div'

  return (
    <Container
      onClick={onClick}
      type={clickable ? 'button' : undefined}
      className={`w-full text-left flex flex-col gap-3 p-4 bg-harbor-card border border-border rounded-lg ${clickable ? 'hover:bg-harbor-elevated/40 transition-colors cursor-pointer' : ''} ${className}`}
    >
      <div className="flex items-start gap-3">
        {leadingIcon && <div className="flex-shrink-0">{leadingIcon}</div>}
        <div className="flex-1 min-w-0">
          <div className="text-[13.5px] font-semibold text-text-primary truncate">
            {title}
          </div>
          {subtitle && (
            <div className="text-[11.5px] text-text-tertiary mt-0.5 truncate tabular-nums">
              {subtitle}
            </div>
          )}
        </div>
        {trailing && <div className="flex-shrink-0">{trailing}</div>}
      </div>

      {rows.length > 0 && (
        <div className="grid grid-cols-2 gap-3 pt-3 border-t border-border">
          {rows.map((r, i) => (
            <div key={i} className="min-w-0">
              <div className="text-[11px] uppercase tracking-wider text-text-tertiary">
                {r.label}
              </div>
              <div
                className={`font-mono tabular-nums text-[13px] ${emphasisClasses[r.emphasis ?? 'default']} whitespace-nowrap truncate`}
              >
                {r.value}
              </div>
            </div>
          ))}
        </div>
      )}

      {footer && <div className="flex gap-2 pt-1">{footer}</div>}
    </Container>
  )
}
