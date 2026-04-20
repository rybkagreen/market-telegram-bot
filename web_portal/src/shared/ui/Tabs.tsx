interface Tab {
  id: string
  label: string
  icon?: string
}

interface TabsProps {
  tabs: Tab[]
  active: string
  onChange: (id: string) => void
  className?: string
}

export function Tabs({ tabs, active, onChange, className = '' }: TabsProps) {
  return (
    <div role="tablist" className={`flex gap-1 p-1 bg-harbor-elevated rounded-lg ${className}`}>
      {tabs.map((tab) => {
        const selected = active === tab.id
        return (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={selected}
            tabIndex={selected ? 0 : -1}
            className={`flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-md transition-all duration-fast flex-1 justify-center
              ${selected
                ? 'bg-harbor-card text-text-primary shadow-sm'
                : 'text-text-secondary hover:text-text-primary'
              }`}
            onClick={() => onChange(tab.id)}
          >
            {tab.icon && <span>{tab.icon}</span>}
            {tab.label}
          </button>
        )
      })}
    </div>
  )
}
