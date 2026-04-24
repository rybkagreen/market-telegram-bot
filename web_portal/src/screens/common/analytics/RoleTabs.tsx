import type { InsightsRole } from '@/api/analytics'

interface RoleTabsProps {
  role: InsightsRole
  onChange: (role: InsightsRole) => void
}

export function RoleTabs({ role, onChange }: RoleTabsProps) {
  return (
    <div
      role="tablist"
      className="inline-flex p-1 bg-harbor-card border border-border rounded-lg"
    >
      <TabButton active={role === 'advertiser'} onClick={() => onChange('advertiser')}>
        Реклама
      </TabButton>
      <TabButton active={role === 'owner'} onClick={() => onChange('owner')}>
        Каналы
      </TabButton>
    </div>
  )
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={[
        'px-4 py-1.5 rounded-md text-sm font-semibold transition-colors',
        active
          ? 'bg-accent text-white shadow'
          : 'text-text-secondary hover:text-text-primary',
      ].join(' ')}
    >
      {children}
    </button>
  )
}
