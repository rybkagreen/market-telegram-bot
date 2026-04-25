import { useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Button } from '@/components/ui'
import { Text } from '@/components/ui/Text'
import { useMyLegalProfile } from '@/hooks/useLegalProfileQueries'
import styles from './LegalProfileSetup.module.css'

const PORTAL_URL = import.meta.env.VITE_PORTAL_URL

export default function LegalProfileSetup() {
  const navigate = useNavigate()
  const { data: profile } = useMyLegalProfile()

  return (
    <ScreenShell>
      <div className={styles.layout}>
        <div className={styles.icon}>🔒</div>
        <Text variant="lg" weight="bold" as="h2" className={styles.title}>
          Юридический профиль
        </Text>

        {profile ? (
          <>
            <div className={styles.bulletCard}>
              <Text variant="sm">
                Ваш профиль заполнен. Для редактирования перейдите на портал.
              </Text>
              <Text variant="xs" className={styles.profileInfo}>
                Статус: {profile.legal_status}
                {profile.inn && ` · ИНН: ${profile.inn}`}
              </Text>
            </div>
          </>
        ) : (
          <div className={styles.bulletCard}>
            <Text variant="sm">
              Для защиты ваших персональных данных (152-ФЗ) заполнение юридического профиля доступно только через защищённый веб-портал.
            </Text>
          </div>
        )}

        <Button
          variant="primary"
          fullWidth
          onClick={() => window.open(`${PORTAL_URL}/legal-profile`, '_blank')}
        >
          {profile ? '✏️ Редактировать на портале' : '📋 Заполнить на портале'}
        </Button>

        <button
          className={styles.skipButton}
          onClick={() => navigate(-1)}
        >
          ← Назад
        </button>
      </div>
    </ScreenShell>
  )
}
