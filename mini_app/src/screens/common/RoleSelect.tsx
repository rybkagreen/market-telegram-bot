import { useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { MenuButton, Card, StatusPill } from '@/components/ui'
import { PLAN_INFO } from '@/lib/constants'
import { useMe } from '@/hooks/queries'
import styles from './RoleSelect.module.css'

export default function RoleSelect() {
  const navigate = useNavigate()
  const { data: user } = useMe()
  const role = user?.current_role

  return (
    <ScreenShell>
      <p className={styles.sectionTitle}>Кем вы хотите работать?</p>

      <div className={styles.list}>
        <MenuButton
          icon="📣"
          iconBg="var(--rh-accent-muted)"
          title="Рекламодатель"
          subtitle="Размещаю рекламу в каналах"
          onClick={() => navigate('/adv')}
        />
        <MenuButton
          icon="📺"
          iconBg="var(--rh-accent-2-muted)"
          title="Владелец канала"
          subtitle="Принимаю рекламу в своём канале"
          onClick={() => navigate('/own')}
        />
      </div>

      <Card title="Ваш текущий статус" className={styles.statusCard}>
        <div className={styles.pills}>
          {(role === 'advertiser' || role === 'both') && (
            <StatusPill status="info">📣 Рекламодатель</StatusPill>
          )}
          {(role === 'owner' || role === 'both') && (
            <StatusPill status="purple">📺 Владелец</StatusPill>
          )}
          {user && (
            <StatusPill status="success">{PLAN_INFO[user.plan].displayName}</StatusPill>
          )}
        </div>
      </Card>
    </ScreenShell>
  )
}
