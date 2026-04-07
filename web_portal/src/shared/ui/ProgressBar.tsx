interface ProgressBarProps {
  value: number
  max?: number
  color?: 'accent' | 'success' | 'warning' | 'danger'
  showLabel?: boolean
  className?: string
}

const colorClasses: Record<string, string> = {
  accent: 'bg-accent',
  success: 'bg-success',
  warning: 'bg-warning',
  danger: 'bg-danger',
}

export function ProgressBar({ value, max = 100, color = 'accent', showLabel = false, className = '' }: ProgressBarProps) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100))

  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      <div className="w-full h-2 bg-harbor-elevated rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-fast ${colorClasses[color]}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      {showLabel && (
        <div className="text-xs text-text-tertiary text-right">{Math.round(pct)}%</div>
      )}
    </div>
  )
}
