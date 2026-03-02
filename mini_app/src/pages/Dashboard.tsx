import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { analyticsApi } from '@/api/analytics'
import { campaignsApi } from '@/api/campaigns'
import { useAuthStore } from '@/store/authStore'
import { Badge } from '@/components/ui/Badge'
import { ActivityChart } from '@/components/charts/ActivityChart'
import { DashboardSkeleton } from '@/components/ui/Skeleton'

// ─── Утилиты ────────────────────────────────────────────────────

function fmtCredits(n: number) {
  return n.toLocaleString('ru-RU')
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString('ru-RU', {
    day: 'numeric', month: 'short',
  })
}

function daysLeft(iso: string | null) {
  if (!iso) return null
  const diff = new Date(iso).getTime() - Date.now()
  return Math.max(0, Math.ceil(diff / 86_400_000))
}

const PLAN_COLORS: Record<string, string> = {
  free:     'var(--neutral)',
  starter:  'var(--info)',
  pro:      'var(--accent-400)',
  business: 'var(--warning)',
}

// ─── Компоненты ─────────────────────────────────────────────────

function StatCard({
  label, value, sub, delay = 0,
}: {
  label: string
  value: string | number
  sub: string
  delay?: number
}) {
  return (
    <motion.div
      className="card"
      initial={{ opacity: 0, scale: 0.94 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay, duration: 0.25 }}
      style={{ display: 'flex', flexDirection: 'column', gap: 4 }}
    >
      <p style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 500 }}>
        {label}
      </p>
      <p className="font-mono" style={{ fontSize: 22, fontWeight: 700, lineHeight: 1 }}>
        {value}
      </p>
      <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>{sub}</p>
    </motion.div>
  )
}

// ─── Страница ───────────────────────────────────────────────────

export default function Dashboard() {
  const user = useAuthStore(s => s.user)

  const { data: summary, isLoading } = useQuery({
    queryKey: ['analytics', 'summary'],
    queryFn: analyticsApi.summary,
    staleTime: 60_000,
  })

  const { data: activity } = useQuery({
    queryKey: ['analytics', 'activity', 7],
    queryFn: () => analyticsApi.activity(7),
    staleTime: 60_000,
  })

  const { data: campaigns } = useQuery({
    queryKey: ['campaigns', 'recent'],
    queryFn: () => campaignsApi.list({ limit: 3 }),
    staleTime: 30_000,
  })

  if (isLoading) return <DashboardSkeleton />

  const s = summary!
  const days = daysLeft(s.plan_expires_at)
  const planColor = PLAN_COLORS[s.plan] ?? 'var(--text-secondary)'
  const usdApprox = Math.round(s.credits / 90)

  return (
    <div className="page-content page-enter">

      {/* Шапка */}
      <div style={{ marginBottom: 16 }}>
        <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
          Привет, {user?.first_name ?? 'пользователь'} 👋
        </p>
        <h1 style={{ fontSize: 22, fontWeight: 700 }}>Market Bot</h1>
      </div>

      {/* Карточка баланса */}
      <motion.div
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        style={{
          background: 'linear-gradient(135deg, #1a2035 0%, #0f1521 100%)',
          border: '1px solid var(--border-accent)',
          borderRadius: 20,
          padding: 24,
          marginBottom: 12,
          boxShadow: 'var(--shadow-glow)',
        }}
      >
        <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>
          Баланс
        </p>
        <p className="font-mono" style={{ fontSize: 36, fontWeight: 700, lineHeight: 1, marginBottom: 4 }}>
          {fmtCredits(s.credits)} кр
        </p>
        <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 16 }}>
          ≈ ${usdApprox}
        </p>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 18 }}>
          <span style={{
            background: planColor + '22',
            color: planColor,
            padding: '3px 10px',
            borderRadius: 6,
            fontSize: 12,
            fontWeight: 700,
          }}>
            {s.plan.toUpperCase()}
          </span>
          {days !== null && (
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              {days > 0 ? `${days} дней` : 'Истёк'}
            </span>
          )}
        </div>

        <Link
          to="/billing"
          className="btn btn-primary"
          style={{ textDecoration: 'none', display: 'flex' }}
        >
          + Пополнить
        </Link>
      </motion.div>

      {/* Стат-карточки 2×2 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 12 }}>
        <StatCard
          label="Отправлено"
          value={fmtCredits(s.total_sent)}
          sub="всего"
          delay={0.05}
        />
        <StatCard
          label="Успешность"
          value={`${s.success_rate}%`}
          sub="в среднем"
          delay={0.1}
        />
        <StatCard
          label="Кампаний"
          value={s.campaigns_count}
          sub="всего создано"
          delay={0.15}
        />
        <StatCard
          label="ИИ-генерации"
          value={s.ai_included > 0 ? `${s.ai_generations_used}/${s.ai_included}` : '—'}
          sub={s.ai_included > 0 ? 'в месяц' : 'недоступно'}
          delay={0.2}
        />
      </div>

      {/* График активности */}
      <motion.div
        className="card"
        style={{ marginBottom: 12 }}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.25 }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
          <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>
            📈 Активность за 7 дней
          </p>
          <p className="font-mono" style={{ fontSize: 13, color: 'var(--accent-400)' }}>
            {fmtCredits(activity?.total_sent ?? 0)}
          </p>
        </div>
        {activity && <ActivityChart data={activity.points} />}
      </motion.div>

      {/* Последние кампании */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
        <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>
          Последние кампании
        </p>
        <Link to="/campaigns" style={{ fontSize: 12, color: 'var(--accent-400)', textDecoration: 'none' }}>
          Все →
        </Link>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {!campaigns?.items?.length ? (
          <div className="card" style={{ textAlign: 'center', padding: 24 }}>
            <p style={{ fontSize: 28, marginBottom: 8 }}>📭</p>
            <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>
              Кампаний пока нет
            </p>
          </div>
        ) : (
          campaigns.items.map((c, i) => (
            <motion.div
              key={c.id}
              className="card"
              style={{ display: 'flex', alignItems: 'center', gap: 12, cursor: 'pointer' }}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.3 + i * 0.06 }}
              onClick={() => window.Telegram?.WebApp?.HapticFeedback?.impactOccurred('light')}
            >
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                  <Badge status={c.status as any} />
                  <p style={{
                    fontSize: 14, fontWeight: 500,
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  }}>
                    {c.title}
                  </p>
                </div>
                <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  {c.status === 'error'
                    ? (c.error_msg ?? 'Ошибка рассылки')
                    : `Отправлено: ${c.sent_count} • ${fmtDate(c.created_at)}`
                  }
                </p>
              </div>
              <span style={{ color: 'var(--text-muted)', fontSize: 16, flexShrink: 0 }}>›</span>
            </motion.div>
          ))
        )}
      </div>

    </div>
  )
}
