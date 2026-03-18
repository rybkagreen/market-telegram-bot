import { motion } from 'motion/react'

interface ScreenTransitionProps {
  children: React.ReactNode
}

export function ScreenTransition({ children }: ScreenTransitionProps) {
  return (
    <motion.div
      initial={{ opacity: 0, x: 12 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -12 }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
      style={{ width: '100%', height: '100%' }}
    >
      {children}
    </motion.div>
  )
}
