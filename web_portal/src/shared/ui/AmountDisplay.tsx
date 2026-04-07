interface AmountDisplayProps {
  value: string | number
  currency?: '₽' | 'USD' | '€'
  variant?: 'positive' | 'negative' | 'neutral'
  className?: string
}

/**
 * AmountDisplay — runtime-computed oklch() для динамических цветовых оттенков.
 * style={{}} разрешён исключительно для oklch() вычислений (исключение из правил).
 */
export function AmountDisplay({ value, currency = '₽', variant = 'neutral', className = '' }: AmountDisplayProps) {
  const num = typeof value === 'string' ? parseFloat(value) : value
  const isPositive = variant === 'positive' || num >= 0
  const absNum = Math.abs(num)

  // OKLCH цвета по Design System v2
  const colorStyle = isPositive
    ? 'oklch(0.72 0.18 160)'  // success green
    : 'oklch(0.65 0.22 25)'   // danger red

  const formatted = new Intl.NumberFormat('ru-RU', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(absNum)

  return (
    <span className={`font-mono tabular-nums ${className}`} style={{ color: colorStyle }}>
      {isPositive ? '' : '−'}{formatted} {currency}
    </span>
  )
}
