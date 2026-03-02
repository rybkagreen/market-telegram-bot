export function ProgressBar({
  value,
  max = 100,
  variant = 'default',
  height = 4,
}: {
  value: number
  max?: number
  variant?: 'default' | 'success' | 'danger'
  height?: number
}) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100))

  const colors = {
    default: 'var(--accent-500)',
    success: 'var(--success)',
    danger:  'var(--danger)',
  }

  return (
    <div style={{
      height, background: 'var(--bg-elevated)',
      borderRadius: height / 2, overflow: 'hidden',
    }}>
      <div style={{
        height: '100%',
        width: `${pct}%`,
        background: colors[variant],
        borderRadius: height / 2,
        transition: 'width 600ms ease',
      }} />
    </div>
  )
}
