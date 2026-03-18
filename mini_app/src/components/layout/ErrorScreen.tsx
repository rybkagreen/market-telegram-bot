import styles from './ErrorScreen.module.css'

export function ErrorScreen() {
  return (
    <div className={styles.container}>
      <span className={styles.icon}>⚠️</span>
      <h2 className={styles.title}>Не удалось войти</h2>
      <p className={styles.message}>
        Попробуйте закрыть и открыть приложение заново
      </p>
      <button
        className={styles.button}
        onClick={() => window.location.reload()}
      >
        Попробовать снова
      </button>
      <a
        className={styles.link}
        href="https://t.me/RekharborBot"
        rel="noreferrer"
      >
        Открыть бота
      </a>
    </div>
  )
}
