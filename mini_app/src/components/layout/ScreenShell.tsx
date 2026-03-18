import styles from './ScreenShell.module.css'

interface ScreenShellProps {
  children: React.ReactNode
  className?: string
  noPadding?: boolean
}

export function ScreenShell({ children, className, noPadding }: ScreenShellProps) {
  const paddingClass = noPadding ? styles.noPadding : styles.withPadding
  const combined = [styles.shell, paddingClass, className].filter(Boolean).join(' ')

  return (
    <div className={combined}>
      {children}
    </div>
  )
}
