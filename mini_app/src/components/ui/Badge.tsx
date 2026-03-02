type Status = 'done' | 'running' | 'queued' | 'error' | 'draft' | 'paused' | 'cancelled'

const cfg: Record<Status, { label: string; color: string; bg: string; pulse?: boolean }> = {
  done:      { label: 'Завершено',   color: 'var(--success)', bg: 'var(--success-dim)' },
  running:   { label: 'Активна',     color: 'var(--info)',    bg: 'var(--info-dim)',    pulse: true },
  queued:    { label: 'В очереди',   color: 'var(--warning)', bg: 'var(--warning-dim)' },
  error:     { label: 'Ошибка',      color: 'var(--danger)',  bg: 'var(--danger-dim)'  },
  draft:     { label: 'Черновик',    color: 'var(--neutral)', bg: 'var(--neutral-dim)' },
  paused:    { label: 'На паузе',    color: 'var(--neutral)', bg: 'var(--neutral-dim)' },
  cancelled: { label: 'Отменено',    color: 'var(--neutral)', bg: 'var(--neutral-dim)' },
}

export function Badge({ status }: { status: Status }) {
  const { label, color, bg, pulse } = cfg[status] ?? cfg.draft
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 5,
      padding: '3px 8px', borderRadius: 6,
      fontSize: 11, fontWeight: 600, lineHeight: 1,
      color, background: bg,
    }}>
      <span style={{
        width: 6, height: 6, borderRadius: '50%',
        background: color, flexShrink: 0,
        animation: pulse ? 'badgePulse 1.5s ease-in-out infinite' : 'none',
      }} />
      {label}
    </span>
  )
}
