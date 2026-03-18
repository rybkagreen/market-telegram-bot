import { useNavigate } from 'react-router-dom'
import { motion } from 'motion/react'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Notification, StatusPill, Button } from '@/components/ui'
import { PLAN_INFO } from '@/lib/constants'
import type { Plan } from '@/lib/types'
import { useMe } from '@/hooks/queries'
import styles from './Plans.module.css'

interface PlanConfig {
  key: Plan
  features: string[]
  featured?: boolean
}

const PLANS: PlanConfig[] = [
  {
    key: 'free',
    features: ['1 активная кампания', 'Только пост 24ч', 'Базовая аналитика'],
  },
  {
    key: 'starter',
    features: [
      '5 активных кампаний',
      'Пост 24ч и 48ч',
      'AI-генерация текста × 3',
      'Расширенная аналитика',
    ],
  },
  {
    key: 'pro',
    featured: true,
    features: [
      '20 активных кампаний',
      'Пост 24ч, 48ч, 7 дней',
      'AI-генерация текста × 20',
      'Полная аналитика + экспорт',
      'Высокий приоритет',
    ],
  },
  {
    key: 'business',
    features: [
      'Безлимит кампаний',
      'Все 5 форматов (закрепы!)',
      'Безлимит AI-генерации',
      'API доступ',
      'Наивысший приоритет',
    ],
  },
]

const containerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.07 } },
}

const itemVariants = {
  hidden: { opacity: 0, y: 10 },
  visible: { opacity: 1, y: 0 },
}

export default function Plans() {
  const navigate = useNavigate()
  const { data: user } = useMe()
  const currentPlan = user?.plan ?? 'free'
  const currentInfo = PLAN_INFO[currentPlan]

  return (
    <ScreenShell>
      <Notification type="info">
        Текущий тариф: {currentInfo.displayName} · {currentInfo.price > 0 ? `${currentInfo.price} ₽/мес` : 'Бесплатно'}
      </Notification>

      <motion.div
        className={styles.list}
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        {PLANS.map(({ key, features, featured }) => {
          const info = PLAN_INFO[key]
          const isCurrent = key === currentPlan

          return (
            <motion.div
              key={key}
              variants={itemVariants}
              className={`${styles.card} ${featured ? styles.featured : ''}`}
            >
              <div className={styles.header}>
                <span className={styles.planName}>{info.displayName}</span>
                <span className={styles.price}>
                  <span className={styles.priceValue}>
                    {info.price > 0 ? info.price.toLocaleString('ru-RU') : '0'}
                  </span>
                  <span className={styles.priceSuffix}>/мес</span>
                </span>
              </div>

              <ul className={styles.features}>
                {features.map((f) => (
                  <li key={f} className={styles.feature}>
                    <span className={styles.check}>✓</span>
                    <span>{f}</span>
                  </li>
                ))}
              </ul>

              {isCurrent ? (
                <StatusPill status="info">Ваш тариф</StatusPill>
              ) : (
                <Button variant="secondary" fullWidth onClick={() => navigate('/topup')}>
                  Выбрать {info.displayName}
                </Button>
              )}
            </motion.div>
          )
        })}
      </motion.div>
    </ScreenShell>
  )
}
