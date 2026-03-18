import type { ReactNode } from 'react'
import styles from './Timeline.module.css'

interface TimelineEvent {
  id: string | number
  icon?: string
  title: string
  subtitle?: string
  date?: string
  variant?: 'default' | 'success' | 'warning' | 'danger'
  content?: ReactNode
}

interface TimelineProps {
  events: TimelineEvent[]
}

export function Timeline({ events }: TimelineProps) {
  return (
    <div className={styles.timeline}>
      {events.map((event, i) => (
        <div key={event.id} className={styles.item}>
          <div className={styles.left}>
            <div className={`${styles.dot} ${styles[event.variant ?? 'default']}`}>
              {event.icon ?? '●'}
            </div>
            {i < events.length - 1 && <div className={styles.line} />}
          </div>
          <div className={styles.body}>
            <div className={styles.header}>
              <span className={styles.title}>{event.title}</span>
              {event.date && <span className={styles.date}>{event.date}</span>}
            </div>
            {event.subtitle && <div className={styles.subtitle}>{event.subtitle}</div>}
            {event.content && <div className={styles.content}>{event.content}</div>}
          </div>
        </div>
      ))}
    </div>
  )
}
