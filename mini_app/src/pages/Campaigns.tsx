import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { campaignsApi, CampaignItem } from '@/api/campaigns'
import { Badge } from '@/components/ui/Badge'
import { ProgressBar } from '@/components/ui/ProgressBar'
import { Skeleton } from '@/components/ui/Skeleton'
import { CampaignDetail } from '@/components/CampaignDetail'
import { CreateCampaignForm } from '@/components/CreateCampaignForm'

// ─── Табы фильтрации ─────────────────────────────────────────────

const TABS = [
  { key: '',         label: 'Все'        },
  { key: 'running',  label: '🔄 Активные'  },
  { key: 'done',     label: '✅ Готовые'   },
  { key: 'draft',    label: '📝 Черновики' },
  { key: 'error',    label: '❌ Ошибки'   },
]

// ─── Скелетон одной карточки ────────────────────────────────────

function CampaignCardSkeleton() {
  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <Skeleton width={68} height={20} radius={6} />
        <Skeleton width="60%" height={16} />
      </div>
      <Skeleton height={4} radius={2} />
      <Skeleton width="40%" height={12} />
    </div>
  )
}

// ─── Страница ───────────────────────────────────────────────────

export default function Campaigns() {
  const [activeTab, setActiveTab] = useState('')
  const [selectedCampaign, setSelectedCampaign] = useState<CampaignItem | null>(null)
  const [page, setPage] = useState(1)
  const [showCreateForm, setShowCreateForm] = useState(false)

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['campaigns', activeTab, page],
    queryFn: () => campaignsApi.list({
      status: activeTab || undefined,
      page,
      limit: 10,
    }),
    staleTime: 30_000,
  })

  const handleTabChange = (key: string) => {
    setActiveTab(key)
    setPage(1)
    window.Telegram?.WebApp?.HapticFeedback?.selectionChanged()
  }

  const handleCardClick = (c: CampaignItem) => {
    setSelectedCampaign(c)
    window.Telegram?.WebApp?.HapticFeedback?.impactOccurred('light')
  }

  const handleCreateSuccess = (campaignId: number) => {
    setShowCreateForm(false)
    // Обновляем список кампаний
    window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success')
  }

  return (
    <div className="page-content page-enter">

      {/* Заголовок с кнопкой создания */}
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700 }}>Кампании</h1>
          {data && (
            <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 2 }}>
              {data.total} всего
            </p>
          )}
        </div>
        <button
          className="btn btn-primary"
          onClick={() => setShowCreateForm(true)}
          style={{
            padding: '10px 20px',
            borderRadius: 12,
            fontSize: 13,
            fontWeight: 600,
          }}
        >
          + Новая
        </button>
      </div>

      {/* Горизонтальные табы */}
      <div style={{
        display: 'flex', gap: 8, overflowX: 'auto',
        paddingBottom: 4, marginBottom: 16,
        scrollbarWidth: 'none',
      }}>
        {TABS.map(tab => (
          <button
            key={tab.key}
            onClick={() => handleTabChange(tab.key)}
            style={{
              flexShrink: 0,
              padding: '7px 14px',
              borderRadius: 20,
              border: 'none',
              fontSize: 13,
              fontWeight: 500,
              cursor: 'pointer',
              transition: 'all 150ms',
              background: activeTab === tab.key
                ? 'var(--accent-500)'
                : 'var(--bg-surface)',
              color: activeTab === tab.key
                ? 'white'
                : 'var(--text-secondary)',
              fontFamily: 'var(--font-body)',
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Список кампаний */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>

        {/* Скелетоны при загрузке */}
        {isLoading && Array.from({ length: 5 }).map((_, i) => (
          <CampaignCardSkeleton key={i} />
        ))}

        {/* Пустое состояние */}
        {!isLoading && data?.items.length === 0 && (
          <div className="card" style={{ textAlign: 'center', padding: 40 }}>
            <p style={{ fontSize: 36, marginBottom: 12 }}>📭</p>
            <p style={{ fontSize: 16, fontWeight: 600, marginBottom: 6 }}>
              Кампаний нет
            </p>
            <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
              {activeTab
                ? 'В этой категории пусто'
                : 'Создайте первую кампанию в боте'
              }
            </p>
          </div>
        )}

        {/* Карточки */}
        {data?.items.map((campaign, i) => (
          <motion.div
            key={campaign.id}
            className="card"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.04 }}
            onClick={() => handleCardClick(campaign)}
            style={{ cursor: 'pointer', userSelect: 'none' }}
            whileTap={{ scale: 0.98 }}
          >
            {/* Строка 1: бейдж + название */}
            <div style={{
              display: 'flex', alignItems: 'center', gap: 8,
              marginBottom: 8,
            }}>
              <Badge status={campaign.status as any} />
              <p style={{
                fontSize: 14, fontWeight: 600, flex: 1,
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              }}>
                {campaign.title}
              </p>
              <span style={{ color: 'var(--text-muted)', fontSize: 14 }}>›</span>
            </div>

            {/* Прогресс-бар (только для done/running) */}
            {['done', 'running'].includes(campaign.status) && campaign.sent_count > 0 && (
              <div style={{ marginBottom: 8 }}>
                <ProgressBar
                  value={campaign.sent_count}
                  max={campaign.target_count ?? campaign.sent_count}
                  variant={campaign.status === 'done' ? 'success' : 'default'}
                  height={4}
                />
              </div>
            )}

            {/* Строка 2: метаданные */}
            <div style={{
              display: 'flex', justifyContent: 'space-between',
              fontSize: 12, color: 'var(--text-muted)',
            }}>
              <span>
                {campaign.status === 'error'
                  ? (campaign.error_msg ?? 'Ошибка')
                  : campaign.status === 'draft'
                  ? 'Черновик'
                  : `${campaign.sent_count} отправлено`
                }
              </span>
              <span>
                {new Date(campaign.created_at).toLocaleDateString('ru-RU', {
                  day: 'numeric', month: 'short',
                })}
              </span>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Пагинация */}
      {data && data.pages > 1 && (
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          gap: 12, marginTop: 20,
        }}>
          <button
            className="btn btn-ghost"
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1 || isFetching}
            style={{ width: 44, padding: 0 }}
          >
            ‹
          </button>
          <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
            {page} / {data.pages}
          </span>
          <button
            className="btn btn-ghost"
            onClick={() => setPage(p => Math.min(data.pages, p + 1))}
            disabled={page === data.pages || isFetching}
            style={{ width: 44, padding: 0 }}
          >
            ›
          </button>
        </div>
      )}

      {/* Bottom sheet деталей */}
      <CampaignDetail
        campaign={selectedCampaign}
        onClose={() => setSelectedCampaign(null)}
      />

      {/* Модальное окно создания кампании */}
      <AnimatePresence>
        {showCreateForm && (
          <motion.div
            className="modal-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setShowCreateForm(false)}
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: 'rgba(0, 0, 0, 0.8)',
              backdropFilter: 'blur(4px)',
              zIndex: 1000,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: 20,
            }}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0, y: 20 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.9, opacity: 0, y: 20 }}
              onClick={(e) => e.stopPropagation()}
              style={{
                width: '100%',
                maxWidth: 500,
                maxHeight: '90vh',
                overflow: 'auto',
              }}
            >
              <CreateCampaignForm
                onSuccess={handleCreateSuccess}
                onCancel={() => setShowCreateForm(false)}
              />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

    </div>
  )
}
