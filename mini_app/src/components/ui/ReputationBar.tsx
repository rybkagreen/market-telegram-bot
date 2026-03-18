import styles from './ReputationBar.module.css'

interface ReputationBarProps {
  score: number   // 0–10
  label?: string
  showScore?: boolean
}

export function ReputationBar({ score, label, showScore = true }: ReputationBarProps) {
  const pct = Math.min(100, Math.max(0, (score / 10) * 100))

  return (
    <div className={styles.wrapper}>
      {(label || showScore) && (
        <div className={styles.header}>
          {label && <span className={styles.label}>{label}</span>}
          {showScore && <span className={styles.score}>{score.toFixed(1)}</span>}
        </div>
      )}
      <div className={styles.track}>
        <div className={styles.fill} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}
