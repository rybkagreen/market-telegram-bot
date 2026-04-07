interface Category {
  id: string
  label: string
  icon: string
}

interface CategoryGridProps {
  categories: Category[]
  selected?: string[]
  onToggle: (id: string) => void
  multi?: boolean
}

export function CategoryGrid({ categories, selected = [], onToggle }: CategoryGridProps) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
      {categories.map((cat) => {
        const isActive = selected.includes(cat.id)
        return (
          <button
            key={cat.id}
            type="button"
            className={`flex flex-col items-center gap-2 p-4 rounded-lg border transition-all duration-fast cursor-pointer
              ${isActive
                ? 'border-accent bg-accent-muted text-accent shadow-sm'
                : 'border-border bg-harbor-card text-text-secondary hover:border-accent/50 hover:text-text-primary'
              }`}
            onClick={() => onToggle(cat.id)}
            aria-pressed={isActive}
          >
            <span className="text-2xl">{cat.icon}</span>
            <span className="text-sm font-medium text-center leading-tight">{cat.label}</span>
          </button>
        )
      })}
    </div>
  )
}
