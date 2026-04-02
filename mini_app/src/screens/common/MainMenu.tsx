import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'motion/react'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { MenuButton, Notification } from '@/components/ui'
import { useMe } from '@/hooks/queries'
import styles from './MainMenu.module.css'

const containerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.05 } },
}

const itemVariants = {
  hidden: { opacity: 0, y: 8 },
  visible: { opacity: 1, y: 0 },
}

export default function MainMenu() {
  const navigate = useNavigate()
  const { data: user } = useMe()
  const [bannerDismissed, setBannerDismissed] = useState(false)

  const showLegalBanner =
    !bannerDismissed &&
    user?.has_legal_profile === false &&
    user?.legal_profile_skipped_at !== null

  return (
    <ScreenShell>
      <AnimatePresence>
        {showLegalBanner && (
          <motion.div
            key="legal-banner"
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '10px 14px',
              borderRadius: 'var(--rh-radius-md, 12px)',
              background: 'var(--rh-warning-muted, rgba(251,191,36,0.12))',
              border: '1px solid var(--rh-warning, rgba(251,191,36,0.3))',
              marginBottom: 8,
              fontSize: 'var(--rh-text-sm, 14px)',
            }}
          >
            <span style={{ flex: 1 }}>
              Заполните юридический профиль для работы с договорами
            </span>
            <button
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                color: 'var(--rh-accent)',
                fontWeight: 600,
                padding: '4px 8px',
                fontSize: 'var(--rh-text-xs, 12px)',
              }}
              onClick={() => navigate('/legal-profile')}
            >
              Заполнить
            </button>
            <button
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                color: 'var(--rh-text-muted)',
                padding: '4px',
                fontSize: 16,
              }}
              onClick={() => setBannerDismissed(true)}
            >
              ✕
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      <Notification type="info">
        Привет, {user?.first_name ?? 'Гость'}! Выберите действие
      </Notification>

      <p className={styles.sectionTitle}>Меню</p>

      <motion.div
        className={styles.list}
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        {/* Admin Panel Button - Visible only to admins */}
        {user?.is_admin && (
          <motion.div variants={itemVariants}>
            <MenuButton
              icon="🛡️"
              iconBg="var(--rh-danger-muted)"
              title="Админ панель"
              subtitle="Управление платформой"
              onClick={() => navigate('/admin')}
            />
          </motion.div>
        )}

        <motion.div variants={itemVariants}>
          <MenuButton
            icon="👤"
            iconBg="var(--rh-accent-muted)"
            title="Кабинет"
            subtitle="Баланс, статистика, тарифы"
            onClick={() => navigate('/cabinet')}
          />
        </motion.div>

        <motion.div variants={itemVariants}>
          <MenuButton
            icon="🔄"
            iconBg="var(--rh-accent-2-muted)"
            title="Выбрать роль"
            subtitle="Рекламодатель / Владелец"
            onClick={() => navigate('/role')}
          />
        </motion.div>

        <motion.div variants={itemVariants}>
          <MenuButton
            icon="💬"
            iconBg="var(--rh-success-muted)"
            title="Помощь"
            subtitle="FAQ и поддержка"
            onClick={() => navigate('/help')}
          />
        </motion.div>

        <motion.div variants={itemVariants}>
          <MenuButton
            icon="✉️"
            iconBg="var(--rh-warning-muted)"
            title="Обратная связь"
            subtitle="Написать в поддержку"
            onClick={() => navigate('/feedback')}
          />
        </motion.div>
      </motion.div>
    </ScreenShell>
  )
}
