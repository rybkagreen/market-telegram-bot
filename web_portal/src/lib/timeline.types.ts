// ============================================================
// RekHarbor — TimelineEvent Types (Web Portal)
// S31-04 | Shared timeline event contract
// ============================================================

// id format: 'ord-{status}' | 'act-{act_id}' | 'contract-{contract_id}'
export type TimelineEventStatus = 'default' | 'warning' | 'success' | 'danger' | 'info'
export type TimelineEventType = 'placement' | 'ord' | 'act' | 'contract'

export interface TimelineEvent {
  id: string
  type: TimelineEventType
  label: string
  status: TimelineEventStatus
  timestamp: string
  metadata?: Record<string, unknown>
}
