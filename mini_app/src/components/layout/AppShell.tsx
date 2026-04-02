import { Suspense } from 'react'
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
      <AnimatePresence>
        <motion.div
          key={location.pathname}
          className={styles.page}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.12, ease: 'easeOut' }}
        >
          <Suspense fallback={<SplashScreen />}>
            <Outlet />
          </Suspense>
        </motion.div>
      </AnimatePresence>
      <ToastContainer />
    </div>
  )
}
