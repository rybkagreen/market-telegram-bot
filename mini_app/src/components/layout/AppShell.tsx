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

  // NOTE: Current transition is fade-only (120ms). For directional slide
  // transitions, we would need to track navigation direction via
  // `location.state?.direction` or compare history indices.
  // Deferred to future iteration — fade is sufficient for MVP and avoids
  // the complexity of direction tracking in a createBrowserRouter setup
  // (which lacks the `action`/`location` data that HashRouter provides).
  //
  // Future implementation:
  //   const direction = location.state?.direction ?? 'forward'
  //   const x = direction === 'forward' ? 16 : -16
  //   initial={{ opacity: 0, x }}
  //   animate={{ opacity: 1, x: 0 }}
  //   exit={{ opacity: 0, x: direction === 'forward' ? -16 : 16 }}

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
