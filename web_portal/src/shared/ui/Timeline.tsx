interface TimelineEvent {
  id: string
  icon: string
  title: string
  subtitle?: string
  variant?: 'success' | 'warning' | 'danger' | 'default'
}

interface TimelineProps {
  events: TimelineEvent[]
}

const DOT_BG_MAP: Record<string, string> = {
  success: 'bg-success-muted',
  warning: 'bg-warning-muted',
  default: 'bg-border',
}

const DOT_INNER_MAP: Record<string, string> = {
  success: 'bg-success',
  warning: 'bg-warning',
  default: 'bg-border-active',
}

export function Timeline({ events }: TimelineProps) {
  return (
    <div className="flex flex-col">
      {events.map((event, i) => {
        const isFirst = i === 0
        const isLast = i === events.length - 1
        const variant = event.variant ?? 'default'
        const dotBg = DOT_BG_MAP[variant]
        const dotInner = DOT_INNER_MAP[variant]
        const paddingClasses = [isLast && 'pb-0', isFirst && 'pt-1'].filter(Boolean).join(' ')

        return (
          <div key={event.id} className="flex gap-3">
            {/* Timeline line */}
            <div className="flex flex-col items-center">
              <div className={`w-8 h-8 rounded-full ${dotBg} flex items-center justify-center shrink-0`}>
                <div className={`w-4 h-4 rounded-full ${dotInner} flex items-center justify-center text-white text-xs`}>
                  {event.icon}
                </div>
              </div>
              {!isLast && (
                <div className="w-px h-full bg-border my-1" />
              )}
            </div>
            {/* Content */}
            <div className={`pb-6 ${paddingClasses}`}>
              <div className="text-sm font-medium text-text-primary">{event.title}</div>
              {event.subtitle && <div className="text-xs text-text-tertiary mt-0.5">{event.subtitle}</div>}
            </div>
          </div>
        )
      })}
    </div>
  )
}
