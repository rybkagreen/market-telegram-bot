import { AnimatePresence, motion } from 'motion/react'
import { Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { useBackButton } from '@/hooks/useBackButton'
import { SplashScreen } from './SplashScreen'
import { ErrorScreen } from './ErrorScreen'
import { ToastContainer } from './ToastContainer'
import styles from './AppShell.module.css'

export function AppShell() {
  const { isAuthenticated, isLoading } = useAuth()
  useBackButton()
  const location = useLocation()

  if (isLoading) return <SplashScreen />
  if (!isAuthenticated) return <ErrorScreen />

  return (
    <div className={styles.shell}>
      <AnimatePresence mode="wait">
        <motion.div
          key={location.pathname}
          className={styles.page}
          initial={{ opacity: 0, x: 8 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -8 }}
          transition={{ duration: 0.15, ease: 'easeOut' }}
        >
          <Outlet />
        </motion.div>
      </AnimatePresence>
      <ToastContainer />
    </div>
  )
}
