interface Format {
  id: string
  label: string
  description?: string
  icon?: string
  price?: string
}

interface FormatSelectorProps {
  formats: Format[]
  selected?: string
  onSelect: (id: string) => void
}

export function FormatSelector({ formats, selected, onSelect }: FormatSelectorProps) {
  return (
    <div className="flex flex-col gap-2">
      {formats.map((fmt) => {
        const isActive = selected === fmt.id
        return (
          <button
            key={fmt.id}
            type="button"
            className={`flex items-center gap-3 p-4 rounded-lg border transition-all duration-fast cursor-pointer text-left
              ${isActive
                ? 'border-accent bg-accent-muted/30 shadow-sm'
                : 'border-border bg-harbor-card hover:border-accent/50'
              }`}
            onClick={() => onSelect(fmt.id)}
          >
            <span className={`text-lg shrink-0 ${isActive ? 'text-accent' : 'text-text-tertiary'}`}>
              {isActive ? '◉' : '○'}
            </span>
            {fmt.icon && <span className="text-xl shrink-0">{fmt.icon}</span>}
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-text-primary">{fmt.label}</div>
              {fmt.description && <div className="text-xs text-text-tertiary mt-0.5">{fmt.description}</div>}
            </div>
            {fmt.price && (
              <span className="text-sm font-semibold text-accent shrink-0 tabular-nums">{fmt.price}</span>
            )}
          </button>
        )
      })}
    </div>
  )
}
