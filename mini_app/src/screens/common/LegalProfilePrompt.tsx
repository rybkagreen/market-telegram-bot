import { useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Button } from '@/components/ui'
import { Text } from '@/components/ui/Text'
import { useSkipLegalPrompt } from '@/hooks/useLegalProfileQueries'
import styles from './LegalProfilePrompt.module.css'

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
        <div className={styles.icon}>📋</div>
        <Text variant="lg" weight="bold" as="h2" className={styles.title}>
          Заполните юридический профиль
        </Text>
        <div className={styles.bulletCard}>
          <p className={styles.bulletItem}>• Оформление договоров</p>
          <p className={styles.bulletItem}>• Расчёт налогов</p>
          <p className={styles.bulletItem}>• Маркировка рекламы (erid)</p>
        </div>

        <Button variant="primary" fullWidth onClick={() => navigate('/legal-profile')}>
          Заполнить сейчас →
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
