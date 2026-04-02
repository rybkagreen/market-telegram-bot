import { useState } from 'react'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Card, Button, StatGrid, EmptyState, StatusPill, Skeleton, Notification } from '@/components/ui'
import { useBackButton } from '@/hooks/useBackButton'
import { useTelegram } from '@/hooks/useTelegram'
import { useReferralStats } from '@/hooks/queries/useReferralStats'
import { formatDate } from '@/lib/formatters'
import type { ReferralItem } from '@/lib/types'
import styles from './Referral.module.css'

export default function Referral() {
  const { tg } = useTelegram()
  const [copySuccess, setCopySuccess] = useState(false)
  const { data, isLoading, isError, refetch } = useReferralStats()

  useBackButton()

  const handleCopyLink = async () => {
    if (!data?.referral_link) return
    
    try {
      await navigator.clipboard.writeText(data.referral_link)
      setCopySuccess(true)
      tg?.HapticFeedback.notificationOccurred('success')
      setTimeout(() => setCopySuccess(false), 2000)
    } catch {
      tg?.HapticFeedback.notificationOccurred('error')
    }
  }

  const handleShare = () => {
    if (!data?.referral_link) return
    
    // Fallback to clipboard if shareURL not available
    navigator.clipboard.writeText(data.referral_link)
    tg?.HapticFeedback.impactOccurred('light')
  }

  if (isLoading) {
    return (
      <ScreenShell>
        <Card title="🎁 Реферальная программа">
          <Skeleton height={80} />
        </Card>
        <Card title="Статистика">
          <Skeleton height={60} />
        </Card>
        <Card title="Рефералы">
          <Skeleton height={120} />
        </Card>
      </ScreenShell>
    )
  }

  if (isError || !data) {
    return (
      <ScreenShell>
        <Notification type="danger">
          Не удалось загрузить данные о рефералах
        </Notification>
        <Button fullWidth onClick={() => refetch()}>
          Повторить
        </Button>
      </ScreenShell>
    )
  }

  return (
    <ScreenShell>
      {/* S1: Hero — реферальная ссылка */}
      <Card title="🎁 Реферальная программа" className={styles.heroCard}>
        <p className={styles.description}>
          Приглашайте друзей — получайте кредиты за каждую оплату
        </p>
        
        <div className={styles.codeBlock}>
          <span className={styles.codeLabel}>Ваш код:</span>
          <span className={styles.code}>{data.referral_code}</span>
        </div>

        <div className={styles.actions}>
          <Button 
            variant={copySuccess ? 'success' : 'primary'} 
            fullWidth 
            onClick={() => void handleCopyLink()}
          >
            {copySuccess ? '✅ Скопировано' : '📋 Копировать ссылку'}
          </Button>
          
          <Button 
            variant="secondary" 
            fullWidth 
            onClick={handleShare}
          >
            📤 Поделиться
          </Button>
        </div>
      </Card>

      {/* S2: Статистика */}
      <Card title="Статистика">
        <StatGrid
          items={[
            { value: data.total_referrals.toString(), label: 'Приглашено', color: 'blue' },
            { value: data.active_referrals.toString(), label: 'Активных', color: 'green' },
            { 
              value: `${data.total_earned_credits} кр.`, 
              label: 'Заработано', 
              color: 'yellow' 
            },
          ]}
        />
      </Card>

      {/* S3: Список рефералов */}
      <Card title="Рефералы">
        {data.referrals.length === 0 ? (
          <EmptyState
            icon="👥"
            title="Пока нет рефералов"
            description="Поделитесь ссылкой с друзьями"
          />
        ) : (
          <div className={styles.referralList}>
            {data.referrals.map((referral: ReferralItem) => (
              <div key={referral.id} className={styles.referralItem}>
                <div className={styles.referralAvatar}>
                  {referral.username?.charAt(0).toUpperCase() || '👤'}
                </div>
                <div className={styles.referralInfo}>
                  <div className={styles.referralName}>
                    {referral.username || `User #${referral.telegram_id}`}
                  </div>
                  <div className={styles.referralDate}>
                    {formatDate(referral.created_at)}
                  </div>
                </div>
                <StatusPill status={referral.is_active ? 'success' : 'neutral'} size="sm">
                  {referral.is_active ? 'Активен' : 'Новый'}
                </StatusPill>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* S4: Как работает */}
      <Card title="Как это работает">
        <ol className={styles.steps}>
          <li className={styles.step}>
            <span className={styles.stepNumber}>1</span>
            <span>Поделитесь своей ссылкой с другом</span>
          </li>
          <li className={styles.step}>
            <span className={styles.stepNumber}>2</span>
            <span>Друг регистрируется в боте по вашей ссылке</span>
          </li>
          <li className={styles.step}>
            <span className={styles.stepNumber}>3</span>
            <span>После первого пополнения счёта вы получаете бонусные кредиты</span>
          </li>
          <li className={styles.step}>
            <span className={styles.stepNumber}>4</span>
            <span>Нет ограничений — приглашайте сколько угодно друзей</span>
          </li>
        </ol>
      </Card>

      {copySuccess && (
        <div className={styles.toast}>
          <Notification type="success">
            ✅ Ссылка скопирована
          </Notification>
        </div>
      )}
    </ScreenShell>
  )
}
