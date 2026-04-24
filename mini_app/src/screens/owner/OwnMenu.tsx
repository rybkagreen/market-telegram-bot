import { useNavigate } from 'react-router-dom'
import { motion } from 'motion/react'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { MenuButton, Notification, Text } from '@/components/ui'
import { formatCurrency } from '@/lib/formatters'
import { useMe } from '@/hooks/queries/useUserQueries'
import { useMyPlacements } from '@/hooks/queries/usePlacementQueries'
import styles from './OwnMenu.module.css'

const containerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.05 } },
}

const itemVariants = {
  hidden: { opacity: 0, y: 8 },
  visible: { opacity: 1, y: 0 },
}

export default function OwnMenu() {
  const navigate = useNavigate()
  const { data: me } = useMe()
  const { data: pendingPlacements } = useMyPlacements({ role: 'owner', status: 'pending_owner' })

  const earnedRub = me?.earned_rub ?? '0.00'
  const pendingCount = pendingPlacements?.length ?? 0

  return (
    <ScreenShell>
      <Notification type="info">
        <Text variant="sm">📺 Режим владельца канала</Text>
      </Notification>

      <p className={styles.sectionTitle}>Меню владельца</p>

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
            title="Статистика"
            subtitle="Доход, публикации, рейтинг"
            onClick={() => navigate('/analytics?role=owner')}
          />
        </motion.div>

        <motion.div variants={itemVariants}>
          <MenuButton
            icon="📺"
            iconBg="var(--rh-accent-2-muted)"
            title="Мои каналы"
            subtitle="Управление каналами"
            onClick={() => navigate('/own/channels')}
          />
        </motion.div>

        <motion.div variants={itemVariants}>
          <MenuButton
            icon="📋"
            iconBg="var(--rh-warning-muted)"
            title="Заявки"
            badge={pendingCount > 0 ? `${pendingCount} новые` : undefined}
            subtitle="Входящие заявки на размещение"
            onClick={() => navigate('/own/requests')}
          />
        </motion.div>

        <motion.div variants={itemVariants}>
          <MenuButton
            icon="💸"
            iconBg="var(--rh-success-muted)"
            title="Выплаты"
            subtitle={`${formatCurrency(earnedRub)} доступно`}
            onClick={() => navigate('/own/payouts')}
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
