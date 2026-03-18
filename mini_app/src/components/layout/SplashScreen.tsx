import styles from './SplashScreen.module.css'

export function SplashScreen() {
  return (
    <div className={`${styles.container} animate-scale-in`}>
      <span className={`${styles.icon} animate-pulse`}>⚓</span>
      <span className={styles.title}>RekHarborBot</span>
      <div className={styles.subtitle}>
        <span className={`${styles.dot} stagger-1`} style={{ animation: 'pulse 1.2s ease-in-out infinite' }} />
        <span className={`${styles.dot} stagger-2`} style={{ animation: 'pulse 1.2s ease-in-out infinite' }} />
        <span className={`${styles.dot} stagger-3`} style={{ animation: 'pulse 1.2s ease-in-out infinite' }} />
      </div>
    </div>
  )
}
