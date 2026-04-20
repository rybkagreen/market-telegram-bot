import { useMemo, useState } from 'react'
import { Icon } from '@/shared/ui/Icon'
import { ICON_NAMES, FILLED_AVAILABLE, type IconName } from '@/shared/ui/icon-names'
import { ScreenHeader } from '@/shared/ui/ScreenHeader'

export default function DevIcons() {
  const [query, setQuery] = useState('')
  const [variant, setVariant] = useState<'outline' | 'fill'>('outline')
  const [size, setSize] = useState(24)

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return ICON_NAMES as readonly IconName[]
    return (ICON_NAMES as readonly IconName[]).filter((n) => n.toLowerCase().includes(q))
  }, [query])

  return (
    <div className="p-6 max-w-screen-xl mx-auto">
      <ScreenHeader
        title="Icon gallery"
        subtitle={`${filtered.length} / ${ICON_NAMES.length} icons · DEV only`}
      />

      <div className="flex flex-wrap gap-3 mb-6">
        <input
          type="search"
          placeholder="Filter by name..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="px-3 py-2 rounded-lg bg-surface-1 border border-border-subtle text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent-primary"
        />

        <div className="flex gap-1 rounded-lg bg-surface-1 border border-border-subtle p-1">
          <button
            type="button"
            onClick={() => setVariant('outline')}
            aria-pressed={variant === 'outline'}
            className={`px-3 py-1 rounded text-sm ${variant === 'outline' ? 'bg-accent-primary text-white' : 'text-text-secondary'}`}
          >
            Outline
          </button>
          <button
            type="button"
            onClick={() => setVariant('fill')}
            aria-pressed={variant === 'fill'}
            className={`px-3 py-1 rounded text-sm ${variant === 'fill' ? 'bg-accent-primary text-white' : 'text-text-secondary'}`}
          >
            Fill (only {FILLED_AVAILABLE.size})
          </button>
        </div>

        <label className="flex items-center gap-2 text-text-secondary text-sm">
          Size
          <input
            type="range"
            min={16}
            max={48}
            step={4}
            value={size}
            onChange={(e) => setSize(Number(e.target.value))}
          />
          <span className="tabular-nums w-8">{size}</span>
        </label>
      </div>

      <div
        className="grid gap-3"
        style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))' }}
      >
        {filtered.map((name) => {
          const isFillSupported = FILLED_AVAILABLE.has(name)
          const effectiveVariant = variant === 'fill' && !isFillSupported ? 'outline' : variant
          return (
            <button
              key={name}
              type="button"
              onClick={() => navigator.clipboard?.writeText(name)}
              title={`Click to copy "${name}"`}
              className="flex flex-col items-center gap-2 p-3 rounded-lg bg-surface-1 border border-border-subtle hover:border-accent-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary"
            >
              <Icon name={name} size={size} variant={effectiveVariant} />
              <span className="text-xs text-text-secondary font-mono truncate w-full text-center">
                {name}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
