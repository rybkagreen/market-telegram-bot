interface CardProps {
  title?: string
  children: React.ReactNode
  className?: string
  noPadding?: boolean
  onClick?: () => void
}

export function Card({ title, children, className = '', noPadding = false, onClick }: CardProps) {
  const base = `bg-harbor-card border border-border rounded-lg shadow-md ${className}`
  const content = (
    <>
      {title && (
        <div className="px-5 py-4 border-b border-border">
          <h3 className="text-lg font-semibold text-text-primary">{title}</h3>
        </div>
      )}
      <div className={noPadding ? '' : 'p-5'}>
        {children}
      </div>
    </>
  )

  if (onClick) {
    return (
      <button onClick={onClick} className={base}>
        {content}
      </button>
    )
  }

  return <div className={base}>{content}</div>
}
