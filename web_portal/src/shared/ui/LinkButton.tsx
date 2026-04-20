import type { ReactNode } from 'react'

interface LinkButtonProps {
  children: ReactNode
  onClick?: () => void
  tone?: 'accent' | 'secondary' | 'danger'
  underline?: boolean
  className?: string
  type?: 'button' | 'submit'
  disabled?: boolean
}

const toneClasses: Record<string, string> = {
  accent: 'text-accent hover:brightness-115',
  secondary: 'text-text-secondary hover:text-text-primary',
  danger: 'text-danger hover:brightness-115',
}

export function LinkButton({
  children,
  onClick,
  tone = 'accent',
  underline = false,
  className = '',
  type = 'button',
  disabled = false,
}: LinkButtonProps) {
  const cn = [
    'inline-flex items-center gap-1.5 font-medium transition-all',
    'disabled:opacity-50 disabled:cursor-not-allowed',
    underline ? 'underline underline-offset-2' : '',
    toneClasses[tone],
    className,
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <button type={type} className={cn} onClick={onClick} disabled={disabled}>
      {children}
    </button>
  )
}
