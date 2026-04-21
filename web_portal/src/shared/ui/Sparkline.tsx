import { useId } from 'react'

interface SparklineProps {
  data: number[]
  color?: string
  width?: number
  height?: number
  fill?: boolean
  className?: string
}

/**
 * Inline-SVG sparkline. `color` defaults to currentColor so it picks up text color.
 * When `fill` is true, adds a subtle gradient beneath the stroke line.
 */
export function Sparkline({
  data,
  color,
  width = 120,
  height = 32,
  fill = true,
  className = '',
}: SparklineProps) {
  const gradId = `sparkline-grad-${useId().replace(/:/g, '_')}`

  if (!data.length) {
    return <div style={{ width, height }} className={className} />
  }

  const stroke = color ?? 'currentColor'
  const padX = 1
  const padY = 2
  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1
  const stepX = data.length > 1 ? (width - padX * 2) / (data.length - 1) : 0
  const toY = (v: number) => padY + (height - padY * 2) * (1 - (v - min) / range)

  const points = data.map((v, i) => `${padX + i * stepX},${toY(v).toFixed(2)}`)
  const line = `M${points.join(' L')}`
  const area = `${line} L ${padX + (data.length - 1) * stepX},${height - padY} L ${padX},${height - padY} Z`

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className={className}
      aria-hidden="true"
    >
      {fill && (
        <defs>
          <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={stroke} stopOpacity="0.25" />
            <stop offset="100%" stopColor={stroke} stopOpacity="0" />
          </linearGradient>
        </defs>
      )}
      {fill && <path d={area} fill={`url(#${gradId})`} />}
      <path d={line} fill="none" stroke={stroke} strokeWidth="1.6" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  )
}
