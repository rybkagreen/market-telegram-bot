// Timeline event types shared across the web portal

export type TimelineEventStatus = 'default' | 'info' | 'warning' | 'success' | 'danger'

export interface TimelineEvent {
  id: string
  type: 'ord' | 'act' | 'contract' | string
  label: string
  status: TimelineEventStatus
  timestamp: string
}
