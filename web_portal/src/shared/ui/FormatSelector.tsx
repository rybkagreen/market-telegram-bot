interface Format {
  id: string
  label: string
  description?: string
  icon?: string
  price?: string
  disabled?: boolean
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
        const isDisabled = fmt.disabled === true
        return (
          <button
            key={fmt.id}
            type="button"
            disabled={isDisabled}
            className={`flex items-center gap-3 p-4 rounded-lg border transition-all duration-fast text-left
              ${isDisabled
                ? 'border-border bg-harbor-elevated/50 opacity-50 cursor-not-allowed'
                : isActive
                ? 'border-accent bg-accent-muted/30 shadow-sm cursor-pointer hover:border-accent/70'
                : 'border-border bg-harbor-card hover:border-accent/50 cursor-pointer'
              }`}
            onClick={() => { if (!isDisabled) onSelect(fmt.id) }}
          >
            <span className={`text-lg shrink-0 ${isDisabled ? 'text-text-tertiary' : isActive ? 'text-accent' : 'text-text-tertiary'}`}>
              {isDisabled ? '🔒' : isActive ? '◉' : '○'}
            </span>
            {fmt.icon && <span className="text-xl shrink-0">{fmt.icon}</span>}
            <div className="flex-1 min-w-0">
              <div className={`text-sm font-medium ${isDisabled ? 'text-text-tertiary' : 'text-text-primary'}`}>{fmt.label}</div>
              {fmt.description && <div className={`text-xs mt-0.5 ${isDisabled ? 'text-text-tertiary' : 'text-text-tertiary'}`}>{fmt.description}</div>}
            </div>
            {fmt.price && (
              <span className={`text-sm font-semibold shrink-0 tabular-nums ${isDisabled ? 'text-text-tertiary' : 'text-accent'}`}>{fmt.price}</span>
            )}
          </button>
        )
      })}
    </div>
  )
}
