import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Button } from '@/components/ui'
import { useAcceptRules } from '@/hooks/useContractQueries'
import { useMe } from '@/hooks/queries/useUserQueries'

export default function AcceptRules() {
  const navigate = useNavigate()
  const [rulesAccepted, setRulesAccepted] = useState(false)
  const [privacyAccepted, setPrivacyAccepted] = useState(false)

  const { data: user } = useMe()
  const acceptMutation = useAcceptRules()

  const handleAccept = () => {
    acceptMutation.mutate(undefined, {
      onSuccess: () => {
        if (!user?.legal_profile_prompted_at) {
          navigate('/legal-profile-prompt')
        } else {
          navigate('/')
        }
      },
    })
  }

  const checkStyle: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    padding: '12px 16px',
    borderRadius: 'var(--rh-radius-md, 12px)',
    background: 'var(--rh-surface, rgba(255,255,255,0.04))',
    cursor: 'pointer',
    fontSize: 'var(--rh-text-sm, 14px)',
  }

  return (
    <ScreenShell>
      <p style={{ fontWeight: 700, fontSize: 'var(--rh-text-lg, 18px)', marginBottom: 16 }}>
        Правила использования
      </p>

      <label style={checkStyle}>
        <input
          type="checkbox"
          checked={rulesAccepted}
          onChange={(e) => setRulesAccepted(e.target.checked)}
        />
        Я принимаю Правила платформы
      </label>

      <label style={{ ...checkStyle, marginTop: 8 }}>
        <input
          type="checkbox"
          checked={privacyAccepted}
          onChange={(e) => setPrivacyAccepted(e.target.checked)}
        />
        Я принимаю Политику конфиденциальности
      </label>

      <div style={{ marginTop: 24 }}>
      <Button
        variant="primary"
        fullWidth
        disabled={!rulesAccepted || !privacyAccepted || acceptMutation.isPending}
        onClick={handleAccept}
      >
        {acceptMutation.isPending ? '⏳ Принятие...' : 'Принять'}
      </Button>
      </div>
    </ScreenShell>
  )
}
