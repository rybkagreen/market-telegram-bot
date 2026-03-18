import { useNavigate } from 'react-router-dom'
import { motion } from 'motion/react'
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

  return (
    <ScreenShell>
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
