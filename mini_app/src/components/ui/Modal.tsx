import type { ReactNode } from 'react'
import { useEffect } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import styles from './Modal.module.css'

interface ModalProps {
  open: boolean
  onClose: () => void
  title?: string
  children: ReactNode
  footer?: ReactNode
}

export function Modal({ open, onClose, title, children, footer }: ModalProps) {
  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [open, onClose])

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            className={styles.overlay}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            onClick={onClose}
          />
          <motion.div
            className={styles.sheet}
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', stiffness: 400, damping: 40 }}
            role="dialog"
            aria-modal="true"
            aria-label={title}
          >
            <div className={styles.handle} />
            {title && (
              <div className={styles.header}>
                <span className={styles.title}>{title}</span>
                <button type="button" className={styles.close} onClick={onClose}>✕</button>
              </div>
            )}
            <div className={styles.body}>{children}</div>
            {footer && <div className={styles.footer}>{footer}</div>}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
