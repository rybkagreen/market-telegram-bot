import { ScreenShell } from '@/components/layout/ScreenShell'
import { Notification, Card, Button } from '@/components/ui'
import { useHaptic } from '@/hooks/useHaptic'
import styles from './Help.module.css'

const ADV_FAQ = [
  'Как создать кампанию?',
  'Как работает эскроу?',
  'Политика возвратов',
]

const OWNER_FAQ = [
  'Как добавить канал?',
  'Как получить выплату?',
]

export default function Help() {
  const haptic = useHaptic()

  return (
    <ScreenShell>
      <Notification type="info">Если не нашли ответ — напишите нам!</Notification>

      <Card title="Для рекламодателей" className={styles.card}>
        {ADV_FAQ.map((item) => (
          <button key={item} className={styles.faqRow} onClick={() => {}}>
            <span>{item}</span>
            <span className={styles.chevron}>›</span>
          </button>
        ))}
      </Card>

      <Card title="Для владельцев" className={styles.card}>
        {OWNER_FAQ.map((item) => (
          <button key={item} className={styles.faqRow} onClick={() => {}}>
            <span>{item}</span>
            <span className={styles.chevron}>›</span>
          </button>
        ))}
      </Card>

      <Button variant="secondary" fullWidth onClick={() => haptic.tap()}>
        ✉️ Написать в поддержку
      </Button>
    </ScreenShell>
  )
}
