import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { channelsApi, type CategoryStats, type TariffStatsItem } from '@/api/channels'
import { useAuthStore } from '@/store/authStore'
import { ProgressBar } from '@/components/ui/ProgressBar'
import { Skeleton } from '@/components/ui/Skeleton'

// ─── Утилиты ────────────────────────────────────────────────────

function fmtNum(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000)     return `${(n / 1_000).toFixed(0)}K`
  return String(n)
}

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleString('ru-RU', {
    day: 'numeric', month: 'short',
    hour: '2-digit', minute: '2-digit',
  })
}

const TARIFF_COLORS: Record<string, string> = {
  free:     'var(--neutral)',
  starter:  'var(--info)',
  pro:      'var(--accent-400)',
  business: 'var(--warning)',
}

// ─── Карточка тарифа ─────────────────────────────────────────────

function TariffCard({
  item, isCurrentPlan, totalChannels, delay,
}: {
  item: TariffStatsItem
  isCurrentPlan: boolean
  totalChannels: number
  delay: number
}) {
  const color = TARIFF_COLORS[item.tariff]

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.94 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay }}
      style={{
        background: 'var(--bg-surface)',
        border: `2px solid ${isCurrentPlan ? color : 'var(--border)'}`,
        borderRadius: 16, padding: 16,
        position: 'relative',
      }}
    >
      {isCurrentPlan && (
        <span style={{
          position: 'absolute', top: -10, left: 12,
          background: color, color: 'white',
          fontSize: 10, fontWeight: 700,
          padding: '2px 8px', borderRadius: 4,
        }}>
          ВАШ ТАРИФ
        </span>
      )}

      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
        <span style={{
          fontSize: 12, fontWeight: 700, color,
          background: color + '22', padding: '3px 8px', borderRadius: 6,
        }}>
          {item.label}
        </span>
        {item.premium_count > 0 && (
          <span style={{ fontSize: 11, color: 'var(--warning)' }}>
            💎 +{item.premium_count}
          </span>
        )}
      </div>

      <p className="font-mono" style={{
        fontSize: 26, fontWeight: 700, lineHeight: 1, marginBottom: 4,
      }}>
        {item.available.toLocaleString('ru')}
      </p>
      <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 10 }}>
        каналов доступно
      </p>

      <ProgressBar
        value={item.available}
        max={totalChannels}
        variant={['pro', 'business'].includes(item.tariff) ? 'success' : 'default'}
        height={4}
      />
      <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
        {item.percent_of_total}% от базы
      </p>
    </motion.div>
  )
}

// ─── Строка категории (разворачивается по тапу) ──────────────────

function CategoryRow({
  cat, userPlan, index,
}: {
  cat: CategoryStats
  userPlan: string
  index: number
}) {
  const [open, setOpen] = useState(false)
  const userAvail = cat.available_by_tariff[userPlan] ?? 0
  const pct = cat.total > 0 ? Math.round(userAvail / cat.total * 100) : 0

  return (
    <motion.div
      className="card"
      initial={{ opacity: 0, x: -6 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.3 + index * 0.04 }}
      onClick={() => {
        setOpen(o => !o)
        window.Telegram?.WebApp?.HapticFeedback?.selectionChanged()
      }}
      style={{ cursor: 'pointer', marginBottom: 8 }}
      whileTap={{ scale: 0.98 }}
    >
      {/* Строка заголовка */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
        <p style={{ fontSize: 14, fontWeight: 600 }}>{cat.category}</p>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="font-mono" style={{ fontSize: 12, color: 'var(--accent-400)' }}>
            {userAvail} / {cat.total}
          </span>
          <span style={{ color: 'var(--text-muted)', fontSize: 14 }}>
            {open ? '▾' : '›'}
          </span>
        </div>
      </div>

      <ProgressBar
        value={userAvail}
        max={cat.total}
        variant={pct === 100 ? 'success' : pct > 50 ? 'default' : 'danger'}
        height={4}
      />
      <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
        {pct}% доступно на вашем тарифе
      </p>

      {/* Развёрнутый вид */}
      {open && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          style={{ marginTop: 14, overflow: 'hidden' }}
        >
          {/* Доступность по всем тарифам */}
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 12 }}>
            {Object.entries(cat.available_by_tariff).map(([tariff, count]) => (
              <span key={tariff} style={{
                fontSize: 11, fontWeight: 600,
                padding: '3px 8px', borderRadius: 6,
                background: TARIFF_COLORS[tariff] + '22',
                color: TARIFF_COLORS[tariff],
              }}>
                {tariff.toUpperCase()}: {count}
              </span>
            ))}
          </div>

          {/* Топ каналы */}
          {cat.top_channels.length > 0 && (
            <>
              <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>
                Крупнейшие каналы:
              </p>
              {cat.top_channels.map((ch, i) => (
                <div key={ch.id} style={{
                  display: 'flex', justifyContent: 'space-between',
                  padding: '6px 0', fontSize: 13,
                  borderBottom: i < cat.top_channels.length - 1
                    ? '1px solid var(--border)' : 'none',
                }}>
                  <span style={{ color: 'var(--text-secondary)' }}>
                    {ch.username ? `@${ch.username}` : ch.title}
                  </span>
                  <span className="font-mono" style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                    {fmtNum(ch.subscribers)}
                  </span>
                </div>
              ))}
            </>
          )}
        </motion.div>
      )}
    </motion.div>
  )
}

// ─── Скелетон ───────────────────────────────────────────────────

function ChannelsSkeleton() {
  return (
    <div className="page-content" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <Skeleton height={44} width="70%" />
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        {[...Array(4)].map((_, i) => <Skeleton key={i} height={110} radius={16} />)}
      </div>
      <Skeleton height={20} width="40%" />
      {[...Array(5)].map((_, i) => <Skeleton key={i} height={72} radius={14} />)}
    </div>
  )
}

// ─── Главная страница ────────────────────────────────────────────

export default function Channels() {
  const user = useAuthStore(s => s.user)
  const currentPlan = user?.plan ?? 'free'
  const navigate = useNavigate()
  
  // Состояние для выбора каналов сравнения
  const [selectedForCompare, setSelectedForCompare] = useState<number[]>([])

  const { data, isLoading } = useQuery({
    queryKey: ['channels', 'stats'],
    queryFn: channelsApi.stats,
    staleTime: 10 * 60_000,  // 10 мин на фронте (бэкенд кэширует 1 час)
  })

  // Переход к сравнению когда выбрано 2+ канала
  useEffect(() => {
    if (selectedForCompare.length >= 2) {
      // Показываем floating кнопку но не переходим автоматически
    }
  }, [selectedForCompare])

  if (isLoading) return <ChannelsSkeleton />

  const d = data!

  return (
    <div className="page-content page-enter">

      {/* Заголовок с большой цифрой */}
      <div style={{ marginBottom: 16 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 6 }}>База каналов</h1>
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 12 }}>
          <p className="font-mono" style={{ fontSize: 32, fontWeight: 700, lineHeight: 1, color: 'var(--accent-400)' }}>
            {d.total_channels.toLocaleString('ru')}
          </p>
          <div style={{ paddingBottom: 2 }}>
            <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>Telegram-каналов</p>
            <p style={{ fontSize: 11, color: 'var(--success)', fontWeight: 600 }}>
              +{d.added_last_7d} за неделю
            </p>
          </div>
        </div>
        <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
          Обновлено: {fmtDate(d.last_updated)}
        </p>
      </div>

      {/* Карточки тарифов 2×2 */}
      <p style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', marginBottom: 10 }}>
        ДОСТУПНО ПО ТАРИФАМ
      </p>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 20 }}>
        {d.tariff_stats.map((item, i) => (
          <TariffCard
            key={item.tariff}
            item={item}
            isCurrentPlan={item.tariff === currentPlan}
            totalChannels={d.total_channels}
            delay={i * 0.06}
          />
        ))}
      </div>

      {/* CTA для не-business */}
      {currentPlan !== 'business' && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          style={{
            background: 'linear-gradient(135deg, rgba(99,102,241,0.12), rgba(139,92,246,0.08))',
            border: '1px solid var(--border-accent)',
            borderRadius: 14,
            padding: '14px 16px',
            marginBottom: 20,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 12,
          }}
        >
          <div>
            <p style={{ fontSize: 13, fontWeight: 600, marginBottom: 2 }}>
              Нужно больше каналов?
            </p>
            <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              Upgrade открывает крупные каналы
            </p>
          </div>
          <Link
            to="/billing"
            style={{
              textDecoration: 'none', flexShrink: 0,
              background: 'var(--accent-500)', color: 'white',
              padding: '8px 14px', borderRadius: 10,
              fontSize: 13, fontWeight: 600,
            }}
          >
            Upgrade ↗
          </Link>
        </motion.div>
      )}

      {/* Список категорий */}
      <p style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', marginBottom: 10 }}>
        КАТЕГОРИИ — {d.total_categories}
      </p>
      {d.categories.map((cat, i) => (
        <CategoryRow
          key={cat.category}
          cat={cat}
          userPlan={currentPlan}
          index={i}
        />
      ))}

      {/* Floating кнопка сравнения */}
      {selectedForCompare.length >= 2 && (
        <motion.div
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 50 }}
          style={{
            position: 'fixed',
            bottom: 100,
            left: '50%',
            transform: 'translateX(-50%)',
            background: 'var(--accent-500)',
            color: 'white',
            padding: '12px 20px',
            borderRadius: 12,
            boxShadow: '0 4px 20px rgba(99,102,241,0.4)',
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            zIndex: 1000,
          }}
        >
          <span style={{ fontSize: 14, fontWeight: 600 }}>
            📊 Сравнить ({selectedForCompare.length})
          </span>
          <button
            onClick={() => navigate(`/comparison?ids=${selectedForCompare.join(',')}`)}
            style={{
              background: 'white',
              color: 'var(--accent-500)',
              border: 'none',
              padding: '6px 12px',
              borderRadius: 8,
              fontSize: 13,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Открыть
          </button>
          <button
            onClick={() => setSelectedForCompare([])}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'white',
              fontSize: 18,
              cursor: 'pointer',
              padding: '4px',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            ✕
          </button>
        </motion.div>
      )}

    </div>
  )
}
