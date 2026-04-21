import { Icon } from './Icon'
import type { IconName } from './icon-names'

type Variant = 'primary' | 'secondary' | 'danger' | 'success' | 'ghost'
type Size = 'sm' | 'md' | 'lg'

interface ButtonProps {
  variant?: Variant
  size?: Size
  icon?: boolean
  iconLeft?: IconName
  iconRight?: IconName
  fullWidth?: boolean
  loading?: boolean
  disabled?: boolean
  children?: React.ReactNode
  onClick?: (e: React.MouseEvent<HTMLButtonElement>) => void
  className?: string
  type?: 'button' | 'submit'
  title?: string
  'aria-label'?: string
}

const sizeClasses: Record<Size, string> = {
  sm: 'h-8 px-3 text-[13px] gap-1.5',
  md: 'h-10 px-4 text-sm gap-2',
  lg: 'h-12 px-5 text-[15px] gap-2.5',
}

const iconOnlySizeClasses: Record<Size, string> = {
  sm: 'h-8 w-8',
  md: 'h-10 w-10',
  lg: 'h-12 w-12',
}

const iconPixelSize: Record<Size, number> = {
  sm: 14,
  md: 16,
  lg: 18,
}

const spinnerPixelSize: Record<Size, string> = {
  sm: 'h-3.5 w-3.5',
  md: 'h-4 w-4',
  lg: 'h-[18px] w-[18px]',
}

const variantClasses: Record<Variant, string> = {
  primary:
    'bg-accent text-accent-text border border-transparent font-semibold ' +
    'hover:bg-accent-hover active:scale-[0.98] ' +
    'shadow-[0_1px_0_0_oklch(1_0_0_/_0.08)_inset,0_1px_2px_oklch(0_0_0_/_0.25)]',
  secondary:
    'bg-harbor-elevated text-text-primary border border-transparent font-medium ' +
    'hover:text-text-primary hover:border-border-active active:scale-[0.98]',
  danger:
    'bg-danger-muted text-danger border border-transparent font-medium ' +
    'hover:border-danger/30 active:scale-[0.98]',
  success:
    'bg-success-muted text-success border border-transparent font-medium ' +
    'hover:border-success/30 active:scale-[0.98]',
  ghost:
    'bg-transparent text-text-secondary border border-transparent font-medium ' +
    'hover:bg-harbor-elevated hover:text-text-primary active:scale-[0.98]',
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
  'aria-label': ariaLabel,
}: ButtonProps) {
  const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
    if (loading || disabled) return
    onClick?.(e)
  }

  const sizes = icon ? iconOnlySizeClasses : sizeClasses
  const cn = [
    'relative inline-flex items-center justify-center rounded-md whitespace-nowrap',
    'transition-[background-color,border-color,color,transform] duration-150 ease-out select-none',
    'cursor-pointer disabled:opacity-50 disabled:pointer-events-none disabled:cursor-not-allowed',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-border-focus focus-visible:ring-offset-2 focus-visible:ring-offset-harbor-bg',
    sizes[size],
    variantClasses[variant],
    fullWidth ? 'w-full' : '',
    loading ? 'pointer-events-none' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ')

  const iconSize = iconPixelSize[size]

  return (
    <button
      type={type}
      className={cn}
      onClick={handleClick}
      disabled={disabled || loading}
      title={title}
      aria-label={ariaLabel}
      aria-busy={loading || undefined}
    >
      <span
        className={`inline-flex items-center ${sizeClasses[size].includes('gap-1.5') ? 'gap-1.5' : sizeClasses[size].includes('gap-2.5') ? 'gap-2.5' : 'gap-2'} ${loading ? 'opacity-0' : ''}`}
      >
        {iconLeft && <Icon name={iconLeft} size={iconSize} />}
        {children}
        {iconRight && <Icon name={iconRight} size={iconSize} />}
      </span>
      {loading && (
        <span className="absolute inset-0 flex items-center justify-center" aria-hidden="true">
          <span
            className={`${spinnerPixelSize[size]} rounded-full border-2 border-current border-t-transparent animate-spin opacity-60`}
          />
        </span>
      )}
    </button>
  )
}
