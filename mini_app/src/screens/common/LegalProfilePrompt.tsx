import { useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Button } from '@/components/ui'
import { useSkipLegalPrompt } from '@/hooks/useLegalProfileQueries'

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
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          textAlign: 'center',
          gap: 16,
          padding: '24px 0',
        }}
      >
        <div style={{ fontSize: 64 }}>📋</div>
        <h2 style={{ margin: 0, fontSize: 'var(--rh-text-lg, 18px)', fontWeight: 700 }}>
          Заполните юридический профиль
        </h2>
        <div
          style={{
            textAlign: 'left',
            padding: '12px 16px',
            borderRadius: 'var(--rh-radius-md, 12px)',
            background: 'var(--rh-surface, rgba(255,255,255,0.04))',
            width: '100%',
          }}
        >
          <p style={{ margin: '0 0 6px', fontSize: 'var(--rh-text-sm, 14px)', color: 'var(--rh-text-muted)' }}>
            • Оформление договоров
          </p>
          <p style={{ margin: '0 0 6px', fontSize: 'var(--rh-text-sm, 14px)', color: 'var(--rh-text-muted)' }}>
            • Расчёт налогов
          </p>
          <p style={{ margin: 0, fontSize: 'var(--rh-text-sm, 14px)', color: 'var(--rh-text-muted)' }}>
            • Маркировка рекламы (erid)
          </p>
        </div>

        <Button variant="primary" fullWidth onClick={() => navigate('/legal-profile')}>
          Заполнить сейчас →
        </Button>

        <button
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--rh-text-muted, rgba(255,255,255,0.5))',
            fontSize: 'var(--rh-text-sm, 14px)',
            cursor: 'pointer',
            padding: '8px',
          }}
          disabled={skipMutation.isPending}
          onClick={handleSkip}
        >
          {skipMutation.isPending ? 'Сохранение...' : 'Заполнить позже'}
        </button>
      </div>
    </ScreenShell>
  )
}
