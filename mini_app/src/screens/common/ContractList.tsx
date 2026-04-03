import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Skeleton, EmptyState } from '@/components/ui'
import { Text } from '@/components/ui/Text'
import { ContractCard } from '@/components/ContractCard'
import { useContracts } from '@/hooks/useContractQueries'
import { api } from '@/api/client'
import * as Sentry from '@sentry/react'
import styles from './ContractList.module.css'

export default function ContractList() {
  const navigate = useNavigate()
  const { data, isLoading } = useContracts()
  const [viewerOpen, setViewerOpen] = useState(false)
  const [viewerHtml, setViewerHtml] = useState('')
  const [viewerLoading, setViewerLoading] = useState(false)

  const openRulesViewer = async () => {
    setViewerOpen(true)
    setViewerLoading(true)
    try {
      const res = await api.get('contracts/platform-rules/text').json<{ html: string }>()
      setViewerHtml(res.html)
    } catch (err) {
      Sentry.captureException(err)
      setViewerHtml('<p style="color:#e74c3c">Не удалось загрузить текст.</p>')
    } finally {
      setViewerLoading(false)
    }
  }

  // Rules — один пункт (объединяем platform_rules + privacy_policy)
  const hasRules = data?.items.some(c =>
    c.contract_type === 'platform_rules' || c.contract_type === 'privacy_policy'
  )

  // Остальные договоры
  const otherContracts = data?.items.filter(c =>
    c.contract_type !== 'platform_rules' && c.contract_type !== 'privacy_policy'
  ) || []

  return (
    <ScreenShell>
      <Text variant="lg" weight="bold" as="p" className={styles.pageTitle}>
        Мои договоры
      </Text>

      {isLoading ? (
        <>
          <Skeleton height={100} />
          <Skeleton height={100} />
        </>
      ) : !data?.items.length ? (
        <EmptyState icon="📄" title="Договоров пока нет" description="Договоры появятся после начала работы на платформе" />
      ) : (
        <>
          {/* Rules — единая строка */}
          {hasRules && (
            <div className={styles.rulesRow}>
              <span className={styles.rulesLabel}>
                📋 Правила и Политика конфиденциальности
                {' '}
                <span className={styles.rulesAccepted}>✓ Принято</span>
              </span>
              <button
                onClick={openRulesViewer}
                className={styles.readButton}
              >
                📖 Читать
              </button>
            </div>
          )}

          {/* Other contracts — стандартные карточки */}
          {otherContracts.map((contract) => (
            <ContractCard
              key={contract.id}
              contract={contract}
              onView={() => navigate(`/contracts/${contract.id}`)}
              onSign={() => navigate(`/contracts/${contract.id}`)}
            />
          ))}
        </>
      )}

      {/* Text Viewer Modal */}
      {viewerOpen && (
        <div
          className={styles.viewerOverlay}
          onClick={() => setViewerOpen(false)}
        >
          <div
            className={styles.viewerContainer}
            onClick={(e) => e.stopPropagation()}
          >
            <div className={styles.viewerHeader}>
              <Text variant="md" weight="semibold" as="h3" className={styles.viewerTitle}>
                Правила и Политика конфиденциальности
              </Text>
              <button onClick={() => setViewerOpen(false)} className={styles.viewerClose}>✕</button>
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
