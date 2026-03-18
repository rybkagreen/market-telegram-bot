import styles from './StatGrid.module.css'

interface StatItem {
  value: string
  label: string
  color?: 'blue' | 'green' | 'yellow' | 'purple'
}

interface StatGridProps {
  items: StatItem[]
}

export function StatGrid({ items }: StatGridProps) {
  return (
    <div className={styles.grid}>
      {items.map((item, i) => (
        <div key={i} className={styles.item}>
          <div className={`${styles.value} ${item.color ? styles[item.color] : ''}`}>
            {item.value}
          </div>
          <div className={styles.label}>{item.label}</div>
        </div>
      ))}
    </div>
  )
}
