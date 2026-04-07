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
    <div className={`flex gap-1 p-1 bg-harbor-elevated rounded-lg ${className}`}>
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          className={`flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-md transition-all duration-fast flex-1 justify-center
            ${active === tab.id
              ? 'bg-harbor-card text-text-primary shadow-sm'
              : 'text-text-secondary hover:text-text-primary'
            }`}
          onClick={() => onChange(tab.id)}
        >
          {tab.icon && <span>{tab.icon}</span>}
          {tab.label}
        </button>
      ))}
    </div>
  )
}
