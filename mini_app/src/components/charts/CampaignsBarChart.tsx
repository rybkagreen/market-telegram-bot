import {
  BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Cell,
} from 'recharts'
import type { ActivityPoint } from '@/api/analytics'

interface Props {
  data: ActivityPoint[]
}

export function CampaignsBarChart({ data }: Props) {
  return (
    <ResponsiveContainer width="100%" height={160}>
      <BarChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -28 }}>
        <XAxis
          dataKey="date"
          tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
          axisLine={false} tickLine={false}
        />
        <YAxis hide />
        <Tooltip
          contentStyle={{
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border)',
            borderRadius: 8, fontSize: 12,
          }}
          cursor={{ fill: 'var(--bg-hover)' }}
        />
        <Bar dataKey="sent" radius={[4, 4, 0, 0]} name="Отправлено">
          {data.map((entry, i) => (
            <Cell
              key={i}
              fill={entry.sent > 0 ? '#6366F1' : 'var(--bg-elevated)'}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
