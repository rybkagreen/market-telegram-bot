import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'
import type { TopicItem } from '@/api/analytics'

const COLORS = [
  '#6366F1', '#10B981', '#F59E0B', '#EF4444',
  '#3B82F6', '#8B5CF6', '#EC4899', '#14B8A6',
]

interface Props {
  data: TopicItem[]
}

export function DonutChart({ data }: Props) {
  if (!data.length) return (
    <div style={{ textAlign: 'center', padding: 24, color: 'var(--text-muted)', fontSize: 13 }}>
      Нет данных
    </div>
  )

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
      {/* Donut */}
      <div style={{ flexShrink: 0 }}>
        <ResponsiveContainer width={140} height={140}>
          <PieChart>
            <Pie
              data={data}
              dataKey="count"
              nameKey="topic"
              cx="50%" cy="50%"
              innerRadius={42} outerRadius={64}
              paddingAngle={3}
              strokeWidth={0}
            >
              {data.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border)',
                borderRadius: 8,
                fontSize: 12,
              }}
              formatter={(value: number, name: string) => [
                `${value} кампаний`, name
              ]}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Легенда */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 6 }}>
        {data.slice(0, 6).map((item, i) => (
          <div key={item.topic} style={{
            display: 'flex', alignItems: 'center', gap: 8, fontSize: 12,
          }}>
            <div style={{
              width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
              background: COLORS[i % COLORS.length],
            }} />
            <span style={{
              flex: 1, color: 'var(--text-secondary)',
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            }}>
              {item.topic}
            </span>
            <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>
              {item.percentage}%
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
