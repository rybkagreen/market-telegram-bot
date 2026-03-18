import styles from './StepIndicator.module.css'

interface StepIndicatorProps {
  total: number
  current: number
  labels?: string[]
}

export function StepIndicator({ total, current, labels }: StepIndicatorProps) {
  return (
    <div className={styles.wrapper}>
      <div className={styles.dots}>
        {Array.from({ length: total }, (_, i) => {
          const state = i < current ? 'done' : i === current ? 'active' : 'pending'
          return (
            <div key={i} className={styles.dotWrap}>
              <div className={`${styles.dot} ${styles[state]}`} />
              {i < total - 1 && (
                <div className={`${styles.line} ${i < current ? styles.lineDone : ''}`} />
              )}
            </div>
          )
        })}
      </div>
      {labels && labels[current] && (
        <div className={styles.label}>{labels[current]}</div>
      )}
    </div>
  )
}
