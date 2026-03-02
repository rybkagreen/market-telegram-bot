import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { analyticsApi } from '@/api/analytics'
import { useAuthStore } from '@/store/authStore'
import { DonutChart } from '@/components/charts/DonutChart'
import { CampaignsBarChart } from '@/components/charts/CampaignsBarChart'
import { ProgressBar } from '@/components/ui/ProgressBar'
import { Skeleton } from '@/components/ui/Skeleton'

const PERIOD_TABS = [
  { key: 7,  label: '7д'  },
  { key: 30, label: '30д' },
  { key: 90, label: '90д' },
]

// ─── Blur-оверлей для FREE ────────────────────────────────────────

function LockedOverlay() {
  return (
    <div style={{
      position: 'absolute', inset: 0,
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      gap: 12, zIndex: 10,
      background: 'rgba(8, 11, 18, 0.75)',
      backdropFilter: 'blur(3px)',
      borderRadius: 'inherit',
    }}>
      <span style={{ fontSize: 32 }}>🔒</span>
      <p style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)' }}>
        Нужен тариф PRO
      </p>
      <p style={{ fontSize: 13, color: 'var(--text-muted)', textAlign: 'center', padding: '0 20px' }}>
        Аналитика доступна для PRO и BUSINESS
      </p>
    </div>
  )
}

// ─── Страница ───────────────────────────────────────────────────

export default function Analytics() {
  const user = useAuthStore(s => s.user)
  const [period, setPeriod] = useState(7)

  const isPaidPlan = ['pro', 'business'].includes(user?.plan ?? '')

  const { data: summary, isLoading: loadingSummary } = useQuery({
    queryKey: ['analytics', 'summary'],
    queryFn: analyticsApi.summary,
    staleTime: 60_000,
  })

  const { data: activity, isLoading: loadingActivity } = useQuery({
    queryKey: ['analytics', 'activity', period],
    queryFn: () => analyticsApi.activity(period),
    staleTime: 60_000,
  })

  const { data: topics } = useQuery({
    queryKey: ['analytics', 'topics'],
    queryFn: analyticsApi.topics,
    enabled: isPaidPlan,
    staleTime: 5 * 60_000,
  })

  const { data: topChats } = useQuery({
    queryKey: ['analytics', 'top-chats'],
    queryFn: () => analyticsApi.topChats(10),
    enabled: isPaidPlan,
    staleTime: 5 * 60_000,
  })

  return (
    <div className="page-content page-enter">

      {/* Заголовок + переключатель периода */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700 }}>Аналитика</h1>
        <div style={{ display: 'flex', gap: 4 }}>
          {PERIOD_TABS.map(tab => (
            <button
              key={tab.key}
              onClick={() => setPeriod(tab.key)}
              style={{
                padding: '5px 12px', borderRadius: 8, border: 'none',
                fontSize: 12, fontWeight: 600, cursor: 'pointer',
                transition: 'all 150ms', fontFamily: 'var(--font-body)',
                background: period === tab.key ? 'var(--accent-500)' : 'var(--bg-surface)',
                color: period === tab.key ? 'white' : 'var(--text-muted)',
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Сводные метрики */}
      {loadingSummary ? (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginBottom: 16 }}>
          {[...Array(3)].map((_, i) => <Skeleton key={i} height={72} radius={12} />)}
        </div>
      ) : summary && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginBottom: 16 }}>
          {[
            { label: 'Отправлено', value: summary.total_sent.toLocaleString('ru') },
            { label: 'Успех',      value: `${summary.success_rate}%` },
            { label: 'Охват',      value: `~${Math.round(summary.total_sent * 1.2).toLocaleString('ru')}` },
          ].map(({ label, value }, i) => (
            <motion.div
              key={label}
              className="card"
              style={{ textAlign: 'center', padding: 12 }}
              initial={{ opacity: 0, scale: 0.92 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: i * 0.06 }}
            >
              <p style={{ fontSize: 18, fontWeight: 700, fontFamily: 'var(--font-display)' }}>
                {value}
              </p>
              <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{label}</p>
            </motion.div>
          ))}
        </div>
      )}

      {/* График активности */}
      <div className="card" style={{ marginBottom: 12 }}>
        <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 12 }}>
          Динамика за {period} дней
        </p>
        {loadingActivity
          ? <Skeleton height={160} />
          : activity && <CampaignsBarChart data={activity.points} />
        }
      </div>

      {/* Тематики — заблокировано для FREE */}
      <div className="card" style={{ marginBottom: 12, position: 'relative', overflow: 'hidden' }}>
        <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 12 }}>
          Тематики кампаний
        </p>
        <div style={{ filter: isPaidPlan ? 'none' : 'blur(5px)' }}>
          <DonutChart data={topics?.topics ?? [
            { topic: 'IT', count: 12, percentage: 34 },
            { topic: 'Бизнес', count: 10, percentage: 28 },
            { topic: 'Крипта', count: 6, percentage: 18 },
            { topic: 'Другое', count: 7, percentage: 20 },
          ]} />
        </div>
        {!isPaidPlan && <LockedOverlay />}
      </div>

      {/* Топ чатов — заблокировано для FREE */}
      <div className="card" style={{ position: 'relative', overflow: 'hidden' }}>
        <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 12 }}>
          Топ чатов
        </p>
        <div style={{ filter: isPaidPlan ? 'none' : 'blur(5px)' }}>
          {(isPaidPlan ? (topChats?.chats ?? []) : [
            { title: '@it_startup_hub',   username: 'it_startup_hub',   member_count: 1200, sent_count: 45, success_rate: 97.8 },
            { title: '@crypto_traders_ru', username: 'crypto_traders',   member_count: 45000, sent_count: 38, success_rate: 94.7 },
            { title: '@business_growth',  username: 'business_growth',  member_count: 8900, sent_count: 29, success_rate: 89.6 },
          ]).map((chat, i) => (
            <div key={i} style={{
              display: 'flex', alignItems: 'center', gap: 12,
              padding: '10px 0',
              borderBottom: i < 2 ? '1px solid var(--border)' : 'none',
            }}>
              {/* Номер */}
              <span style={{
                width: 24, textAlign: 'center',
                fontSize: 13, fontWeight: 700, color: 'var(--text-muted)',
                fontFamily: 'var(--font-display)', flexShrink: 0,
              }}>
                {i + 1}
              </span>

              {/* Данные чата */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <p style={{
                  fontSize: 13, fontWeight: 600,
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                }}>
                  {chat.username ? `@${chat.username}` : chat.title}
                </p>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
                  <ProgressBar value={chat.success_rate} variant="success" height={3} />
                  <span style={{
                    fontSize: 11, color: 'var(--success)', fontWeight: 600,
                    flexShrink: 0,
                  }}>
                    {chat.success_rate}%
                  </span>
                </div>
              </div>

              {/* Подписчики */}
              <span style={{ fontSize: 11, color: 'var(--text-muted)', flexShrink: 0 }}>
                {chat.member_count >= 1000
                  ? `${(chat.member_count / 1000).toFixed(1)}K`
                  : chat.member_count}
              </span>
            </div>
          ))}
        </div>
        {!isPaidPlan && <LockedOverlay />}
      </div>

    </div>
  )
}
