import { useNavigate } from 'react-router-dom'
import { motion } from 'motion/react'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { MenuButton, Notification } from '@/components/ui'
import { PLAN_INFO } from '@/lib/constants'
import { useMe } from '@/hooks/queries'
import styles from './AdvMenu.module.css'

const containerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.05 } },
}

const itemVariants = {
  hidden: { opacity: 0, y: 8 },
  visible: { opacity: 1, y: 0 },
}

export default function AdvMenu() {
  const navigate = useNavigate()
  const { data: user } = useMe()
  const plan = user ? PLAN_INFO[user.plan] : null

  return (
    <ScreenShell>
      <Notification type="info">
        <span style={{ fontSize: 'var(--rh-text-sm)' }}>
          📣 Режим рекламодателя · Тариф {plan?.displayName ?? '—'}
        </span>
      </Notification>

      <p className={styles.sectionTitle}>Меню рекламодателя</p>

      <motion.div
        className={styles.list}
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        <motion.div variants={itemVariants}>
          <MenuButton
            icon="📊"
            iconBg="var(--rh-accent-muted)"
            title="Статистика и аналитика"
            subtitle="Кампании, охваты, CTR"
            onClick={() => navigate('/adv/analytics')}
          />
        </motion.div>

        <motion.div variants={itemVariants}>
          <MenuButton
            icon="📣"
            iconBg="var(--rh-success-muted)"
            title="Создать кампанию"
            subtitle="Шаг за шагом до публикации"
            onClick={() => navigate('/adv/campaigns/new/category')}
          />
        </motion.div>

        <motion.div variants={itemVariants}>
          <MenuButton
            icon="📋"
            iconBg="var(--rh-accent-2-muted)"
            title="Мои кампании"
            subtitle="Активные, завершённые"
            onClick={() => navigate('/adv/campaigns')}
          />
        </motion.div>

        <motion.div variants={itemVariants}>
          <MenuButton
            variant="back"
            icon="🔙"
            title="В главное меню"
            onClick={() => navigate('/')}
          />
        </motion.div>
      </motion.div>
    </ScreenShell>
  )
}
