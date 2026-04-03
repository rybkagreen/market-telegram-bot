/**
 * ScreenLayout — unified screen wrapper with header, scrollable content, and footer.
 *
 * Replaces the common pattern of:
 *   <ScreenShell> + manual title/header + inline content
 *
 * Structure:
 *   <header>  — optional title + ScreenNavigation (Back/Home/Admin) + custom actions
 *   <main>    — scrollable content area with safe-area padding
 *   <footer>  — optional persistent actions (e.g., submit buttons)
 *
 * Props:
 *   title       — screen title (renders header when present)
 *   noPadding   — remove default padding from main content area
 *   actions     — custom header actions (right side, e.g., icon buttons)
 *   footer      — footer content (renders sticky footer when present)
 *   navBackTo   — explicit back path for ScreenNavigation (default: navigate(-1))
 *   hideNav     — hide ScreenNavigation entirely (default: false)
 *   className   — additional class on the root container
 *   children    — screen content
 */

import type { ReactNode } from 'react'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { ScreenNavigation } from '@/components/layout/ScreenNavigation'
import { Text } from '@/components/ui/Text'
import styles from './ScreenLayout.module.css'

interface ScreenLayoutProps {
  title?: string
  noPadding?: boolean
  actions?: ReactNode
  footer?: ReactNode
  navBackTo?: string
  hideNav?: boolean
  className?: string
  children: ReactNode
}

export function ScreenLayout({
  title,
  noPadding = false,
  actions,
  footer,
  navBackTo,
  hideNav = false,
  className,
  children,
}: ScreenLayoutProps) {
  const hasHeader = title !== undefined || actions !== undefined || !hideNav

  return (
    <ScreenShell noPadding className={`${styles.layout} ${className ?? ''}`}>
      {/* Header */}
      {hasHeader && (
        <header className={styles.header}>
          {!hideNav && (
            <ScreenNavigation backTo={navBackTo} showHome={false} />
          )}

          {title && (
            <Text variant="lg" weight="semibold" font="display" className={styles.title} truncate>
              {title}
            </Text>
          )}

          {actions && <div className={styles.actions}>{actions}</div>}
        </header>
      )}

      {/* Main scrollable content */}
      <main className={`${styles.main} ${noPadding ? styles.noPadding : styles.withPadding}`}>
        {children}
      </main>

      {/* Footer (optional sticky actions) */}
      {footer && <footer className={styles.footer}>{footer}</footer>}
    </ScreenShell>
  )
}
