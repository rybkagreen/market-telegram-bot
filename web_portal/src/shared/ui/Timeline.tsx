interface TimelineEvent {
  id: string
  icon: string
  title: string
  subtitle?: string
  variant?: 'success' | 'warning' | 'default'
}

interface TimelineProps {
  events: TimelineEvent[]
}

export function Timeline({ events }: TimelineProps) {
  return (
    <div className="flex flex-col">
      {events.map((event, i) => {
        const isFirst = i === 0
        const isLast = i === events.length - 1
        const dotBg = event.variant === 'success' ? 'bg-success-muted' : event.variant === 'warning' ? 'bg-warning-muted' : 'bg-border'
        const dotInner = event.variant === 'success' ? 'bg-success' : event.variant === 'warning' ? 'bg-warning' : 'bg-border-active'

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
            <div className={`pb-6 ${isLast ? 'pb-0' : ''} ${isFirst ? 'pt-1' : ''}`}>
              <div className="text-sm font-medium text-text-primary">{event.title}</div>
              {event.subtitle && <div className="text-xs text-text-tertiary mt-0.5">{event.subtitle}</div>}
            </div>
          </div>
        )
      })}
    </div>
  )
}
