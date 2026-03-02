export function Skeleton({
  width = '100%',
  height = 16,
  radius = 8,
}: {
  width?: string | number
  height?: string | number
  radius?: number
}) {
  return (
    <div
      className="skeleton"
      style={{ width, height, borderRadius: radius }}
      aria-hidden="true"
    />
  )
}

export function DashboardSkeleton() {
  return (
    <div className="page-content" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <Skeleton height={180} radius={20} />
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        <Skeleton height={80} radius={14} />
        <Skeleton height={80} radius={14} />
        <Skeleton height={80} radius={14} />
        <Skeleton height={80} radius={14} />
      </div>
      <Skeleton height={160} radius={14} />
      <Skeleton height={72} radius={14} />
      <Skeleton height={72} radius={14} />
      <Skeleton height={72} radius={14} />
    </div>
  )
}
