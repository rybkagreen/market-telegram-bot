import { PriceRow } from './PriceRow'
import styles from './FeeBreakdown.module.css'

interface FeeRow {
  label: string
  value: string
  tag?: string
  tagVariant?: 'accent' | 'success' | 'warning' | 'danger'
  dim?: boolean
}

interface FeeBreakdownProps {
  rows: FeeRow[]
  total: { label: string; value: string }
}

export function FeeBreakdown({ rows, total }: FeeBreakdownProps) {
  return (
    <div className={styles.breakdown}>
      {rows.map((row, i) => (
        <PriceRow key={i} {...row} />
      ))}
      <div className={styles.total}>
        <span className={styles.totalLabel}>{total.label}</span>
        <span className={styles.totalValue}>{total.value}</span>
      </div>
    </div>
  )
}
