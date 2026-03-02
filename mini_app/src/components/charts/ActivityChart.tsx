import {
  AreaChart, Area, XAxis, YAxis, Tooltip,
  ResponsiveContainer,
} from 'recharts'
import type { ActivityPoint } from '@/api/analytics'

interface Props {
  data: ActivityPoint[]
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: 'var(--bg-elevated)',
      border: '1px solid var(--border)',
      borderRadius: 8,
      padding: '8px 12px',
      fontSize: 13,
    }}>
      <p style={{ color: 'var(--text-muted)', marginBottom: 4 }}>{label}</p>
      <p style={{ color: 'var(--success)', fontWeight: 600 }}>
        Отправлено: {payload[0]?.value ?? 0}
      </p>
      {payload[1]?.value > 0 && (
        <p style={{ color: 'var(--danger)' }}>
          Ошибок: {payload[1].value}
        </p>
      )}
    </div>
  )
}

export function ActivityChart({ data }: Props) {
  return (
    <ResponsiveContainer width="100%" height={140}>
      <AreaChart data={data} margin={{ top: 5, right: 5, bottom: 0, left: -28 }}>
        <defs>
          <linearGradient id="gradSent" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor="#6366F1" stopOpacity={0.35} />
            <stop offset="95%" stopColor="#6366F1" stopOpacity={0} />
          </linearGradient>
        </defs>
        <XAxis
          dataKey="date"
          tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis hide />
        <Tooltip content={<CustomTooltip />} cursor={{ stroke: 'var(--border)', strokeWidth: 1 }} />
        <Area
          type="monotone"
          dataKey="sent"
          stroke="#6366F1"
          strokeWidth={2}
          fill="url(#gradSent)"
          dot={false}
          activeDot={{ r: 4, fill: '#6366F1', strokeWidth: 0 }}
        />
        <Area
          type="monotone"
          dataKey="failed"
          stroke="var(--danger)"
          strokeWidth={1.5}
          fill="transparent"
          dot={false}
          activeDot={{ r: 3, fill: 'var(--danger)', strokeWidth: 0 }}
          strokeDasharray="4 3"
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}
