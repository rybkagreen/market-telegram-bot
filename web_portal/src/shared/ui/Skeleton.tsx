interface SkeletonProps {
  className?: string
  height?: number
}

export function Skeleton({ className = '', height }: SkeletonProps) {
  const style = height ? { height: `${height}px` } : undefined
  return (
    <div
      className={`animate-pulse bg-harbor-elevated rounded-md ${className}`}
      style={style}
    />
  )
}
