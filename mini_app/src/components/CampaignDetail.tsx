import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { campaignsApi, CampaignItem } from '@/api/campaigns'
import { analyticsApi, AIInsights } from '@/api/analytics'
import { useAuthStore } from '@/store/authStore'
import { Badge } from '@/components/ui/Badge'
import { ProgressBar } from '@/components/ui/ProgressBar'
import { Skeleton } from '@/components/ui/Skeleton'

interface Props {
  campaign: CampaignItem | null
  onClose: () => void
}

function fmtDatetime(iso: string | null) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('ru-RU', {
    day: 'numeric', month: 'short',
    hour: '2-digit', minute: '2-digit',
  })
}

export function CampaignDetail({ campaign, onClose }: Props) {
  const qc = useQueryClient()
  const userPlan = useAuthStore(s => s.user?.plan ?? '')

  const { data: stats, isLoading } = useQuery({
    queryKey: ['campaigns', 'stats', campaign?.id],
    queryFn: () => campaignsApi.stats(campaign!.id),
    enabled: !!campaign,
  })

  const { data: aiInsights, isLoading: loadingAi } = useQuery({
    queryKey: ['campaigns', 'ai-insights', campaign?.id],
    queryFn: () => analyticsApi.campaignAiInsights(campaign!.id),
    enabled: !!campaign && ['pro', 'business'].includes(userPlan) && campaign.status === 'done',
    staleTime: 24 * 60 * 60 * 1000, // 24 hours
  })

  const deleteMutation = useMutation({
    mutationFn: () => campaignsApi.delete(campaign!.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['campaigns'] })
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success')
      onClose()
    },
  })

  const duplicateMutation = useMutation({
    mutationFn: () => campaignsApi.duplicate(campaign!.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['campaigns'] })
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success')
      onClose()
    },
  })

  const handleDelete = () => {
    window.Telegram?.WebApp?.showConfirm(
      'Удалить кампанию? Это действие нельзя отменить.',
      (confirmed: boolean) => {
        if (confirmed) deleteMutation.mutate()
      }
    )
  }

  const canDelete = campaign &&
    !['running', 'queued'].includes(campaign.status)

  return (
    <AnimatePresence>
      {campaign && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            style={{
              position: 'fixed', inset: 0,
              background: 'rgba(0,0,0,0.6)',
              backdropFilter: 'blur(2px)',
              zIndex: 100,
            }}
          />

          {/* Sheet */}
          <motion.div
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
            style={{
              position: 'fixed', bottom: 0, left: 0, right: 0,
              background: 'var(--bg-surface)',
              borderRadius: '20px 20px 0 0',
              padding: '0 0 calc(24px + env(safe-area-inset-bottom))',
              zIndex: 101,
              maxHeight: '90dvh',
              overflowY: 'auto',
            }}
          >
            {/* Drag handle */}
            <div style={{ display: 'flex', justifyContent: 'center', padding: '12px 0 8px' }}>
              <div style={{
                width: 36, height: 4,
                background: 'var(--border)',
                borderRadius: 2,
              }} />
            </div>

            <div style={{ padding: '0 20px' }}>
              {/* Заголовок */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
                <Badge status={campaign.status as any} />
                <h2 style={{ fontSize: 17, fontWeight: 700, flex: 1 }}>
                  {campaign.title}
                </h2>
              </div>

              {/* Статистика */}
              {isLoading ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 20 }}>
                  <Skeleton height={20} />
                  <Skeleton height={20} />
                  <Skeleton height={20} />
                </div>
              ) : stats ? (
                <>
                  {/* Прогресс-бар успешности */}
                  {stats.total_logs > 0 && (
                    <div style={{ marginBottom: 20 }}>
                      <div style={{
                        display: 'flex', justifyContent: 'space-between',
                        marginBottom: 6, fontSize: 13,
                      }}>
                        <span style={{ color: 'var(--text-secondary)' }}>Успешность</span>
                        <span style={{ color: 'var(--success)', fontWeight: 600 }}>
                          {stats.success_rate}%
                        </span>
                      </div>
                      <ProgressBar
                        value={stats.success_rate}
                        variant="success"
                        height={6}
                      />
                    </div>
                  )}

                  {/* Метрики 2×2 */}
                  <div style={{
                    display: 'grid', gridTemplateColumns: '1fr 1fr',
                    gap: 10, marginBottom: 20,
                  }}>
                    {[
                      { label: 'Отправлено', value: stats.sent, color: 'var(--success)' },
                      { label: 'Ошибок',     value: stats.failed, color: 'var(--danger)' },
                      { label: 'Пропущено',  value: stats.skipped, color: 'var(--neutral)' },
                      { label: 'Всего',      value: stats.total_logs, color: 'var(--text-primary)' },
                    ].map(({ label, value, color }) => (
                      <div key={label} style={{
                        background: 'var(--bg-elevated)',
                        borderRadius: 12,
                        padding: '12px 14px',
                      }}>
                        <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>
                          {label}
                        </p>
                        <p style={{
                          fontSize: 22, fontWeight: 700,
                          fontFamily: 'var(--font-display)', color,
                        }}>
                          {value}
                        </p>
                      </div>
                    ))}
                  </div>

                  {/* Даты */}
                  <div style={{
                    borderTop: '1px solid var(--border)',
                    paddingTop: 16,
                    marginBottom: 20,
                    display: 'flex', flexDirection: 'column', gap: 8,
                  }}>
                    {[
                      { label: 'Начало', value: fmtDatetime(stats.started_at) },
                      { label: 'Конец',  value: fmtDatetime(stats.finished_at) },
                    ].map(({ label, value }) => (
                      <div key={label} style={{
                        display: 'flex', justifyContent: 'space-between',
                        fontSize: 13,
                      }}>
                        <span style={{ color: 'var(--text-muted)' }}>{label}</span>
                        <span style={{ color: 'var(--text-secondary)' }}>{value}</span>
                      </div>
                    ))}
                  </div>

                  {/* AI-аналитика */}
                  {['pro', 'business'].includes(userPlan) && campaign.status === 'done' && (
                    <div style={{
                      borderTop: '1px solid var(--border)',
                      paddingTop: 16,
                      marginBottom: 20,
                    }}>
                      <div style={{
                        display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12,
                      }}>
                        <span style={{ fontSize: 18 }}>✨</span>
                        <p style={{ fontSize: 14, fontWeight: 700 }}>AI-аналитика</p>
                        {loadingAi && <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Загрузка...</span>}
                      </div>

                      {aiInsights ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                          {/* Оценка */}
                          <div style={{
                            display: 'flex', alignItems: 'center', gap: 8,
                            background: 'var(--bg-elevated)',
                            borderRadius: 10, padding: '8px 12px',
                            width: 'fit-content',
                          }}>
                            <span style={{ fontSize: 16 }}>📊</span>
                            <span style={{ fontSize: 13, fontWeight: 600 }}>
                              Оценка: {aiInsights.performance_grade}
                            </span>
                          </div>

                          {/* Инсайты */}
                          {aiInsights.insights.length > 0 && (
                            <div>
                              <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6 }}>
                                ИНСАЙТЫ
                              </p>
                              <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, color: 'var(--text-secondary)' }}>
                                {aiInsights.insights.map((insight, i) => (
                                  <li key={i} style={{ marginBottom: 4 }}>{insight}</li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {/* Рекомендации */}
                          {aiInsights.recommendations.length > 0 && (
                            <div>
                              <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6 }}>
                                РЕКОМЕНДАЦИИ
                              </p>
                              <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, color: 'var(--text-secondary)' }}>
                                {aiInsights.recommendations.map((rec, i) => (
                                  <li key={i} style={{ marginBottom: 4 }}>{rec}</li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {/* Прогноз (BUSINESS) */}
                          {aiInsights.forecast && (
                            <div style={{
                              background: 'var(--accent-500)',
                              borderRadius: 10, padding: '10px 12px',
                            }}>
                              <p style={{ fontSize: 11, fontWeight: 600, color: 'white', marginBottom: 4 }}>
                                🔮 ПРОГНОЗ
                              </p>
                              <p style={{ fontSize: 13, color: 'white', margin: 0 }}>
                                {aiInsights.forecast}
                              </p>
                            </div>
                          )}

                          {/* A/B тест (BUSINESS) */}
                          {aiInsights.ab_test_suggestion && (
                            <div style={{
                              background: 'var(--warning-dim)',
                              border: '1px solid var(--warning)',
                              borderRadius: 10, padding: '10px 12px',
                            }}>
                              <p style={{ fontSize: 11, fontWeight: 600, color: 'var(--warning)', marginBottom: 4 }}>
                                💡 A/B ТЕСТ
                              </p>
                              <p style={{ fontSize: 13, color: 'var(--text-secondary)', margin: 0 }}>
                                {aiInsights.ab_test_suggestion}
                              </p>
                            </div>
                          )}
                        </div>
                      ) : (
                        <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                          Нажмите кнопку ниже чтобы получить AI-анализ кампании
                        </p>
                      )}

                      {!aiInsights && (
                        <button
                          className="btn"
                          onClick={() => qc.invalidateQueries({ queryKey: ['campaigns', 'ai-insights', campaign.id] })}
                          style={{
                            width: '100%', marginTop: 12,
                            background: 'linear-gradient(135deg, var(--accent-500), var(--accent-600))',
                          }}
                        >
                          ✨ Получить AI-анализ
                        </button>
                      )}
                    </div>
                  )}
                </>
              ) : null}

              {/* Кнопки действий */}
              <div style={{ display: 'flex', gap: 10 }}>
                <button
                  className="btn btn-ghost"
                  onClick={() => duplicateMutation.mutate()}
                  disabled={duplicateMutation.isPending}
                  style={{ flex: 1 }}
                >
                  {duplicateMutation.isPending ? '...' : '📋 Копировать'}
                </button>
                {canDelete && (
                  <button
                    className="btn"
                    onClick={handleDelete}
                    disabled={deleteMutation.isPending}
                    style={{
                      flex: 1,
                      background: 'var(--danger-dim)',
                      color: 'var(--danger)',
                      border: '1px solid var(--danger-dim)',
                    }}
                  >
                    {deleteMutation.isPending ? '...' : '🗑 Удалить'}
                  </button>
                )}
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
