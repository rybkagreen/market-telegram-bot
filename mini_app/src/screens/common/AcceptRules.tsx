import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import DOMPurify from 'dompurify'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Button } from '@/components/ui'
import { Text } from '@/components/ui/Text'
import { useAcceptRules } from '@/hooks/useContractQueries'
import { useMe } from '@/hooks/queries/useUserQueries'
import { api } from '@/api/client'
import * as Sentry from '@sentry/react'
import styles from './AcceptRules.module.css'

export default function AcceptRules() {
  const navigate = useNavigate()
  const [accepted, setAccepted] = useState(false)
  const [viewerOpen, setViewerOpen] = useState(false)
  const [viewerHtml, setViewerHtml] = useState('')
  const [viewerLoading, setViewerLoading] = useState(false)

  const { data: user } = useMe()
  const acceptMutation = useAcceptRules()

  const openViewer = async () => {
    setViewerOpen(true)
    setViewerLoading(true)
    try {
      const data = await api.get('contracts/platform-rules/text').json<{ html: string }>()
      setViewerHtml(DOMPurify.sanitize(data.html, { ALLOWED_TAGS: ['p','strong','em','ul','ol','li','h1','h2','h3','br','a','b','i','u'], ALLOWED_ATTR: ['href','class'] }))
    } catch (err) {
      Sentry.captureException(err)
      setViewerHtml('<p style="color:#e74c3c">Не удалось загрузить текст. Попробуйте позже.</p>')
    } finally {
      setViewerLoading(false)
    }
  }

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

  return (
    <ScreenShell>
      <Text variant="lg" weight="bold" as="h2" className={styles.pageTitle}>
        Правила использования
      </Text>

      {/* Single Rules Card */}
      <div className={styles.rulesCard}>
        <label className={styles.rulesLabel}>
          <input
            type="checkbox"
            checked={accepted}
            onChange={(e) => setAccepted(e.target.checked)}
          />
          Я принимаю Правила платформы и Политику конфиденциальности
        </label>
        <button type="button" className={styles.viewerLink} onClick={openViewer}>
          📖 Прочитать документ
        </button>
      </div>

      {/* Accept Button */}
      <div className={styles.actionWrapper}>
        <Button
          variant="primary"
          fullWidth
          disabled={!accepted || acceptMutation.isPending}
          onClick={handleAccept}
        >
          {acceptMutation.isPending ? '⏳ Принятие...' : 'Принять'}
        </Button>
      </div>

      {/* Text Viewer Modal */}
      {viewerOpen && (
        <div
          className={styles.viewerOverlay}
          role="button"
          tabIndex={0}
          onClick={() => setViewerOpen(false)}
          onKeyDown={(e) => { if (e.key === 'Enter' || (e.key === ' ' && (e.preventDefault() || true))) setViewerOpen(false) }}
        >
          <div
            className={styles.viewerContainer}
            role="presentation"
            onClick={(e) => e.stopPropagation()}
            onKeyDown={(e) => e.stopPropagation()}
          >
            <div className={styles.viewerHeader}>
              <Text variant="md" weight="semibold" as="h3" className={styles.viewerTitle}>
                Правила платформы и Политика конфиденциальности
              </Text>
              <button
                onClick={() => setViewerOpen(false)}
                className={styles.viewerClose}
              >
                ✕
              </button>
            </div>
            <div className={styles.viewerContent}>
              {viewerLoading ? (
                <p className={styles.viewerLoadingText}>Загрузка...</p>
              ) : (
                <div dangerouslySetInnerHTML={{ __html: viewerHtml }} />
              )}
            </div>
          </div>
        </div>
      )}
    </ScreenShell>
  )
}
