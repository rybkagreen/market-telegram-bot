import { Icon } from './Icon'

interface StepIndicatorProps {
  total: number
  current: number
  labels?: string[]
  className?: string
}

export function StepIndicator({ total, current, labels, className = '' }: StepIndicatorProps) {
  return (
    <div className={`overflow-x-auto no-scrollbar -mx-2 px-2 ${className}`}>
      <div className="flex items-center gap-2.5 min-w-max">
        {Array.from({ length: total }).map((_, i) => {
          const idx = i + 1
          const done = idx < current
          const active = idx === current
          const label = labels?.[i]

          const circleClass = done
            ? 'bg-success text-white border-success'
            : active
              ? 'bg-accent text-white border-accent ring-[3px] ring-accent-muted'
              : 'bg-harbor-elevated text-text-tertiary border-border'

          const labelClass = active
            ? 'text-text-primary font-semibold'
            : done
              ? 'text-text-secondary font-medium'
              : 'text-text-tertiary font-medium'

          return (
            <div key={i} className="flex items-center gap-2.5 flex-shrink-0">
              <div className="flex items-center gap-2.5 flex-shrink-0">
                <div
                  className={`w-[26px] h-[26px] rounded-full grid place-items-center text-xs font-display font-bold border transition-all duration-fast ${circleClass}`}
                >
                  {done ? <Icon name="check" size={13} strokeWidth={2.5} /> : idx}
                </div>
                {label && (
                  <span className={`text-[12.5px] whitespace-nowrap hidden md:inline ${labelClass}`}>{label}</span>
                )}
                {label && active && (
                  <span className={`text-[12.5px] whitespace-nowrap md:hidden ${labelClass}`}>{label}</span>
                )}
              </div>
              {i < total - 1 && (
                <div
                  className={`flex-1 h-[1.5px] min-w-[20px] rounded-sm transition-colors ${done ? 'bg-success' : 'bg-border'}`}
                />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
