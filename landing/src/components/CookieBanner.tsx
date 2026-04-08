import { motion, AnimatePresence } from 'motion/react'
import { Link } from 'react-router'
import { useConsent } from '../hooks/useConsent'

export default function CookieBanner() {
  const { consent, accept, decline } = useConsent()

  return (
    <AnimatePresence>
      {consent === 'pending' && (
        <motion.div
          key="cookie-banner"
          role="dialog"
          aria-modal="false"
          aria-label="Уведомление о cookie"
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 40 }}
          transition={{ duration: 0.25, ease: 'easeOut' }}
          className="fixed bottom-4 left-4 right-4 sm:left-auto sm:right-6 sm:max-w-sm z-50 p-5 border"
          style={{
            background: '#fff',
            borderColor: 'var(--color-border)',
            borderRadius: 'var(--radius-xl)',
            boxShadow: 'var(--shadow-elevated)',
            fontFamily: 'var(--font-ui)',
          }}
        >
          <p className="text-sm mb-4" style={{ color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
            Мы используем cookie для улучшения сайта. Нажимая «Принять», вы соглашаетесь с нашей{' '}
            <Link
              to="/privacy"
              className="underline underline-offset-2"
              style={{ color: 'var(--color-brand-blue)' }}
            >
              политикой конфиденциальности
            </Link>
            .
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={accept}
              className="flex-1 py-2 px-4 text-sm font-semibold text-white transition-opacity hover:opacity-90"
              style={{ background: 'var(--color-bg-dark)', borderRadius: 'var(--radius-sm)' }}
            >
              Принять
            </button>
            <button
              onClick={decline}
              className="flex-1 py-2 px-4 text-sm font-medium transition-colors hover:bg-black/10"
              style={{ background: 'var(--color-bg-light)', color: '#333', borderRadius: 'var(--radius-sm)' }}
            >
              Отклонить
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
