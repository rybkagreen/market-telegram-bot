interface ChannelCardProps {
  name: string
  username: string | null
  subscribers: string
  category: string
  price: string
  status?: string
  onClick?: () => void
  isSelected?: boolean
  action?: React.ReactNode
}

export function ChannelCard({ name, username, subscribers, category, price, status, onClick, isSelected, action }: ChannelCardProps) {
  const handleClick = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest('button')) return
    onClick?.()
  }

  return (
    <div
      className={`flex flex-col sm:flex-row sm:items-center gap-3 p-4 border rounded-lg transition-all duration-fast ${
        isSelected
          ? 'border-accent bg-accent/5 shadow-sm'
          : 'border-border bg-harbor-card hover:border-border/80'
      } ${onClick ? 'cursor-pointer' : ''}`}
      onClick={handleClick}
    >
      {/* Top row: avatar + info */}
      <div className="flex items-center gap-3 min-w-0">
        <div className="w-10 h-10 rounded-full bg-accent-muted flex items-center justify-center text-lg shrink-0">
          {category.split(' ')[0]}
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-semibold text-text-primary truncate">{name}</div>
          <div className="text-xs text-text-tertiary">@{username}</div>
          <div className="text-xs text-text-secondary mt-0.5">
            <span>{subscribers} подп.</span>
            {status && <span className="ml-2">· {status}</span>}
          </div>
        </div>
      </div>

      {/* Bottom row: price + action */}
      <div className="flex items-center justify-between sm:justify-end gap-3 pt-2 sm:pt-0 sm:border-0 border-t border-border/50">
        <div className="text-sm font-semibold text-text-primary tabular-nums">
          {price}
          <span className="block text-xs text-text-tertiary font-normal">за пост</span>
        </div>
        {action && (
          <div className="shrink-0">
            {action}
          </div>
        )}
      </div>
    </div>
  )
}
