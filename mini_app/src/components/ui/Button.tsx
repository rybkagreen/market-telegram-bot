import { useHaptic } from '@/hooks/useHaptic'
import styles from './Button.module.css'

interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'danger' | 'success' | 'ghost'
  size?: 'sm' | 'md' | 'lg'
  fullWidth?: boolean
  loading?: boolean
  disabled?: boolean
  children: React.ReactNode
  onClick?: () => void
  className?: string
  type?: 'button' | 'submit'
}

export function Button({
  variant = 'primary',
  size = 'md',
  fullWidth = false,
  loading = false,
  disabled = false,
  children,
  onClick,
  className,
  type = 'button',
}: ButtonProps) {
  const haptic = useHaptic()

  const handleClick = () => {
    if (loading || disabled) return
    haptic.tap()
    onClick?.()
  }

  const cn = [
    styles.button,
    styles[variant],
    styles[size],
    fullWidth ? styles.fullWidth : '',
    disabled ? styles.disabled : '',
    loading ? styles.loading : '',
    className ?? '',
  ].filter(Boolean).join(' ')

  return (
    <button type={type} className={cn} onClick={handleClick} disabled={disabled || loading}>
      <span className={loading ? styles.textHidden : undefined}>{children}</span>
      {loading && <span className={styles.spinner} aria-hidden="true" />}
    </button>
  )
}
