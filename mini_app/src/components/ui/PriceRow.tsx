import styles from './PriceRow.module.css'

interface PriceRowProps {
  label: string
  value: string
  tag?: string
  tagVariant?: 'accent' | 'success' | 'warning' | 'danger'
  dim?: boolean
}

export function PriceRow({ label, value, tag, tagVariant = 'accent', dim = false }: PriceRowProps) {
  return (
    <div className={`${styles.row} ${dim ? styles.dim : ''}`}>
      <span className={styles.label}>{label}</span>
      <span className={styles.right}>
        {tag && <span className={`${styles.tag} ${styles[tagVariant]}`}>{tag}</span>}
        <span className={styles.value}>{value}</span>
      </span>
    </div>
  )
}
