import { AnimatePresence, motion } from 'motion/react'
import { useUiStore } from '@/stores/uiStore'
import type { Toast } from '@/stores/uiStore'
import styles from './ToastContainer.module.css'

const ICONS: Record<Toast['type'], string> = {
  success: '✅',
  error:   '❌',
  warning: '⚠️',
  info:    'ℹ️',
}

const TYPE_CLASS: Record<Toast['type'], string> = {
  success: styles['toast--success'],
  error:   styles['toast--error'],
  warning: styles['toast--warning'],
  info:    styles['toast--info'],
}

export function ToastContainer() {
  const { toasts, removeToast } = useUiStore()

  return (
    <div className={styles.container}>
      <AnimatePresence>
        {toasts.map((toast) => (
          <motion.div
            key={toast.id}
            className={`${styles.toast} ${TYPE_CLASS[toast.type]}`}
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            onClick={() => removeToast(toast.id)}
          >
            <span className={styles.icon}>{ICONS[toast.type]}</span>
            <span className={styles.message}>{toast.message}</span>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}
