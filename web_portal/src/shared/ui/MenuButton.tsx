import { Link } from 'react-router-dom'

interface MenuButtonProps {
  icon: string
  title: string
  subtitle?: string
  href?: string
  onClick?: () => void
  className?: string
}

export function MenuButton({ icon, title, subtitle, href, onClick, className = '' }: MenuButtonProps) {
  const content = (
    <div className={`flex items-center gap-4 p-4 bg-harbor-card border border-border rounded-lg hover:bg-harbor-elevated transition-colors duration-fast cursor-pointer ${className}`}>
      <div className="w-10 h-10 rounded-lg bg-accent-muted flex items-center justify-center text-xl shrink-0">
        {icon}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-text-primary">{title}</p>
        {subtitle && <p className="text-xs text-text-tertiary truncate">{subtitle}</p>}
      </div>
      <svg className="w-5 h-5 text-text-tertiary shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
      </svg>
    </div>
  )

  if (href) {
    return <Link to={href}>{content}</Link>
  }

  if (onClick) {
    return <button onClick={onClick}>{content}</button>
  }

  return <div>{content}</div>
}
