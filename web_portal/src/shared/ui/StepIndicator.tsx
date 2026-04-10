interface StepIndicatorProps {
  total: number
  current: number
  labels?: string[]
}

function getStepState(i: number, current: number): 'done' | 'active' | 'pending' {
  if (i < current) return 'done'
  if (i === current - 1) return 'active'
  return 'pending'
}

export function StepIndicator({ total, current, labels }: StepIndicatorProps) {
  return (
    <div className="mb-6">
      <div className="flex items-center justify-center gap-1 mb-2">
        {Array.from({ length: total }, (_, i) => {
          const state = getStepState(i, current)
          const dotColors: Record<string, string> = {
            done: 'bg-accent',
            active: 'bg-accent ring-4 ring-accent/20',
            pending: 'bg-border',
          }
          return (
            <div key={i} className="flex items-center">
              <div className={`w-3 h-3 rounded-full transition-all duration-fast ${dotColors[state]}`} />
              {i < total - 1 && (
                <div className={`w-6 h-0.5 mx-1 transition-all duration-fast ${i < current ? 'bg-accent' : 'bg-border'}`} />
              )}
            </div>
          )
        })}
      </div>
      {labels && labels[current] && (
        <div className="text-center text-sm text-text-secondary">{labels[current]}</div>
      )}
    </div>
  )
}
