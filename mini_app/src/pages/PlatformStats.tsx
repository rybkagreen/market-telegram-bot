import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'

// ─── Типы ──────────────────────────────────────────────────────

interface PlatformStats {
  active_channels: number
  total_reach: number
  campaigns_launched: number
  campaigns_completed: number
  avg_channel_rating: number
  total_payouts: number
}

// ─── API ────────────────────────────────────────────────────────

async function fetchPlatformStats(): Promise<PlatformStats> {
  const response = await fetch('/api/analytics/stats/public')
  if (!response.ok) {
    throw new Error('Failed to fetch platform stats')
  }
  return response.json()
}

// ─── Утилиты ────────────────────────────────────────────────────

function fmtNumber(n: number): string {
  return n.toLocaleString('ru-RU')
}

// ─── Компоненты ─────────────────────────────────────────────────

function StatCard({
  label,
  value,
  icon,
  delay = 0,
}: {
  label: string
  value: string | number
  icon: string
  delay?: number
}) {
  return (
    <motion.div
      className="card"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.3 }}
    >
      <div className="flex items-center gap-3 mb-2">
        <span className="text-2xl">{icon}</span>
        <span className="text-sm text-muted">{label}</span>
      </div>
      <div className="text-2xl font-bold">{value}</div>
    </motion.div>
  )
}

// ─── Страница ──────────────────────────────────────────────────

export function PlatformStats() {
  const { data, isLoading, error } = useQuery<PlatformStats>({
    queryKey: ['platform-stats'],
    queryFn: fetchPlatformStats,
    refetchInterval: 60000, // Обновлять каждую минуту
  })

  if (isLoading) {
    return (
      <div className="container">
        <div className="text-center text-muted">Загрузка статистики...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="container">
        <div className="text-center text-error">
          ❌ Не удалось загрузить статистику. Попробуйте позже.
        </div>
      </div>
    )
  }

  if (!data) {
    return null
  }

  return (
    <div className="container">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-6"
      >
        <h1 className="text-2xl font-bold mb-2">📊 Статистика платформы</h1>
        <p className="text-muted">
          Публичные метрики RekHarbor — прозрачность и доверие
        </p>
      </motion.div>

      <div className="grid grid-cols-2 gap-4">
        <StatCard
          label="Активных каналов"
          value={fmtNumber(data.active_channels)}
          icon="✅"
          delay={0}
        />
        <StatCard
          label="Суммарный охват"
          value={fmtNumber(data.total_reach)}
          icon="👥"
          delay={0.1}
        />
        <StatCard
          label="Запущено кампаний"
          value={fmtNumber(data.campaigns_launched)}
          icon="🚀"
          delay={0.2}
        />
        <StatCard
          label="Завершено успешно"
          value={fmtNumber(data.campaigns_completed)}
          icon="✅"
          delay={0.3}
        />
        <StatCard
          label="Средний рейтинг"
          value={`${data.avg_channel_rating.toFixed(1)}/10`}
          icon="⭐"
          delay={0.4}
        />
        <StatCard
          label="Выплачено владельцам"
          value={`${fmtNumber(data.total_payouts)} ₽`}
          icon="💰"
          delay={0.5}
        />
      </div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.6 }}
        className="card mt-6"
      >
        <h2 className="text-lg font-semibold mb-3">🔗 Присоединяйтесь</h2>
        <p className="text-muted mb-4">
          Начните использовать платформу для продвижения вашего канала или
          размещения рекламы.
        </p>
        <a
          href="https://t.me/RekHarborBot"
          target="_blank"
          rel="noopener noreferrer"
          className="btn btn-primary w-full"
        >
          Открыть бота в Telegram
        </a>
      </motion.div>
    </div>
  )
}
