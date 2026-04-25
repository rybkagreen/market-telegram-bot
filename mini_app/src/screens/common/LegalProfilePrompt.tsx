import { useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Button } from '@/components/ui'
import { Text } from '@/components/ui/Text'
import { useSkipLegalPrompt } from '@/hooks/useLegalProfileQueries'
import styles from './LegalProfilePrompt.module.css'

const PORTAL_URL = import.meta.env.VITE_PORTAL_URL

export default function LegalProfilePrompt() {
  const navigate = useNavigate()
  const skipMutation = useSkipLegalPrompt()

  const handleSkip = () => {
    skipMutation.mutate(undefined, {
      onSuccess: () => { navigate('/') },
    })
  }

  return (
    <ScreenShell>
      <div className={styles.layout}>
        <div className={styles.icon}>🔒</div>
        <Text variant="lg" weight="bold" as="h2" className={styles.title}>
          Юридический профиль
        </Text>

        {/* 152-ФЗ notice */}
        <div className={styles.bulletCard}>
          <Text variant="sm" className={styles.bulletItem}>
            Для защиты ваших персональных данных (152-ФЗ) заполнение юридического профиля доступно только через защищённый веб-портал.
          </Text>
        </div>

        <div className={styles.bulletCard}>
          <p className={styles.bulletItem}>📋 Оформление договоров</p>
          <p className={styles.bulletItem}>🧾 Расчёт налогов</p>
          <p className={styles.bulletItem}>📌 Маркировка рекламы (erid)</p>
        </div>

        <Button
          variant="primary"
          fullWidth
          onClick={() => window.open(`${PORTAL_URL}/legal-profile`, '_blank')}
        >
          Открыть портал →
        </Button>

        <button
          className={styles.skipButton}
          disabled={skipMutation.isPending}
          onClick={handleSkip}
        >
          {skipMutation.isPending ? 'Сохранение...' : 'Заполнить позже'}
        </button>
      </div>
    </ScreenShell>
  )
}
