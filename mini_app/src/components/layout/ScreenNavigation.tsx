/**
 * ScreenNavigation — compact navigation button bar
 *
 * Renders small icon buttons for Back, Home, and optionally Admin Panel.
 * Used as a fallback/secondary navigation alongside Telegram's native
 * BackButton. Safe for deep screens where users may need a quick escape.
 *
 * Props:
 *   showHome    — show Home button (default: true)
 *   showAdmin   — show Admin button (default: auto-detect via user?.is_admin)
 *   backTo      — explicit back path (default: navigate(-1))
 *   homeTo      — explicit home path (default: '/')
 *   className   — additional CSS classes on the nav container
 */

import { useNavigate, useLocation } from 'react-router-dom'
import { Icon } from '@/components/ui/Icon'
import { useHaptic } from '@/hooks/useHaptic'
import { useMe } from '@/hooks/queries'
import styles from './ScreenNavigation.module.css'

interface ScreenNavigationProps {
  showHome?: boolean
  showAdmin?: boolean
  backTo?: string
  homeTo?: string
  className?: string
}

export function ScreenNavigation({
  showHome = true,
  showAdmin,
  backTo,
  homeTo = '/',
  className,
}: ScreenNavigationProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const haptic = useHaptic()
  const { data: user } = useMe()

  const isAdmin = showAdmin ?? user?.is_admin ?? false
  const isRoot = location.pathname === '/'

  if (isRoot && !isAdmin) return null

  const handleBack = () => {
    haptic.tap()
    if (backTo) {
      navigate(backTo, { replace: true })
    } else {
      navigate(-1)
    }
  }

  const handleHome = () => {
    haptic.tap()
    navigate(homeTo, { replace: true })
  }

  const handleAdmin = () => {
    haptic.tap()
    navigate('/admin')
  }

  const cn = [styles.nav, className ?? ''].filter(Boolean).join(' ')

  return (
    <nav className={cn}>
      {!isRoot && (
        <button
          type="button"
          className={styles.btn}
          onClick={handleBack}
          aria-label="Назад"
          title="Назад"
        >
          <Icon name="ArrowLeft" size={18} />
        </button>
      )}

      {showHome && !isRoot && (
        <button
          type="button"
          className={styles.btn}
          onClick={handleHome}
          aria-label="Главная"
          title="Главная"
        >
          <Icon name="House" size={18} />
        </button>
      )}

      {isAdmin && (
        <button
          type="button"
          className={`${styles.btn} ${styles.admin}`}
          onClick={handleAdmin}
          aria-label="Админ панель"
          title="Админ панель"
        >
          <Icon name="ShieldCheck" size={18} />
        </button>
      )}
    </nav>
  )
}
