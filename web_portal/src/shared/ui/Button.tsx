import { Icon } from './Icon'
import type { IconName } from './icon-names'

interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'danger' | 'success' | 'ghost'
  size?: 'sm' | 'md' | 'lg'
  icon?: boolean
  iconLeft?: IconName
  iconRight?: IconName
  fullWidth?: boolean
  loading?: boolean
  disabled?: boolean
  children?: React.ReactNode
  onClick?: () => void
  className?: string
  type?: 'button' | 'submit'
  title?: string
}

const sizeClasses: Record<string, string> = {
  sm: 'px-3 py-1.5 text-sm min-h-[44px]',
  md: 'px-4 py-2.5 text-base min-h-[44px]',
  lg: 'px-6 py-3 text-base min-h-[52px]',
}

const iconSizeClasses: Record<string, string> = {
  sm: 'p-2.5 text-lg min-h-[44px] min-w-[44px]',
  md: 'p-3 text-xl min-h-[48px] min-w-[48px]',
  lg: 'p-3.5 text-2xl min-h-[52px] min-w-[52px]',
}

const iconPixelSize: Record<string, number> = {
  sm: 14,
  md: 16,
  lg: 18,
}

const variantClasses: Record<string, string> = {
  primary: 'bg-accent text-accent-text hover:brightness-110 active:scale-[0.98] active:brightness-95',
  secondary: 'bg-transparent border border-border-active text-text-primary hover:border-accent hover:text-accent active:scale-[0.98]',
  danger: 'bg-danger-muted text-danger border border-danger-muted hover:brightness-115 active:scale-[0.98]',
  success: 'bg-success-muted text-success border border-success-muted hover:brightness-115 active:scale-[0.98]',
  ghost: 'bg-transparent text-text-secondary hover:bg-harbor-elevated hover:text-text-primary active:scale-[0.98]',
}

export function Button({
  variant = 'primary',
  size = 'md',
  icon = false,
  iconLeft,
  iconRight,
  fullWidth = false,
  loading = false,
  disabled = false,
  children,
  onClick,
  className = '',
  type = 'button',
  title,
}: ButtonProps) {
  const handleClick = () => {
    if (loading || disabled) return
    onClick?.()
  }

  const sizes = icon ? iconSizeClasses : sizeClasses
  const cn = [
    'relative inline-flex items-center justify-center gap-2 rounded-md font-semibold',
    'border transition-all duration-fast select-none whitespace-nowrap',
    'cursor-pointer disabled:opacity-50 disabled:pointer-events-none',
    sizes[size],
    variantClasses[variant],
    fullWidth ? 'w-full' : '',
    loading ? 'pointer-events-none' : '',
    className,
  ].filter(Boolean).join(' ')

  const iconSize = iconPixelSize[size]

  return (
    <button type={type} className={cn} onClick={handleClick} disabled={disabled || loading} title={title}>
      <span className={loading ? 'opacity-0 inline-flex items-center gap-2' : 'inline-flex items-center gap-2'}>
        {iconLeft && <Icon name={iconLeft} size={iconSize} />}
        {children}
        {iconRight && <Icon name={iconRight} size={iconSize} />}
      </span>
      {loading && (
        <span className="absolute inset-0 flex items-center justify-center">
          <span className="w-4 h-4 border-2 border-border border-t-accent rounded-full animate-spin" aria-hidden="true" />
        </span>
      )}
    </button>
  )
}
