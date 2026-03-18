import styles from './Skeleton.module.css'

interface SkeletonProps {
  width?: string | number
  height?: string | number
  radius?: 'sm' | 'md' | 'lg' | 'full'
  lines?: number
  gap?: string
  className?: string
}

export function Skeleton({
  width = '100%',
  height = '1em',
  radius = 'md',
  lines = 1,
  gap = 'var(--rh-space-2)',
  className,
}: SkeletonProps) {
  const style = {
    width: typeof width === 'number' ? `${width}px` : width,
    height: typeof height === 'number' ? `${height}px` : height,
  }

  if (lines <= 1) {
    return (
      <div
        className={`${styles.skeleton} ${styles[radius]} ${className ?? ''}`}
        style={style}
      />
    )
  }

  return (
    <div className={styles.stack} style={{ gap }}>
      {Array.from({ length: lines }, (_, i) => (
        <div
          key={i}
          className={`${styles.skeleton} ${styles[radius]}`}
          style={{
            ...style,
            width: i === lines - 1 ? '65%' : style.width,
          }}
        />
      ))}
    </div>
  )
}
