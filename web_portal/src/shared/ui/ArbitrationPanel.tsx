import type { ReactNode } from 'react'

interface ArbitrationPanelProps {
  title: string
  status?: string
  children: ReactNode
}

export function ArbitrationPanel({ title, status, children }: ArbitrationPanelProps) {
  return (
    <div className="bg-harbor-card border border-border rounded-lg shadow-sm overflow-hidden">
      {(title || status) && (
        <div className="px-5 py-3 border-b border-border flex items-center justify-between">
          <h4 className="text-sm font-semibold text-text-primary">{title}</h4>
          {status && <span className="text-xs text-text-tertiary">{status}</span>}
        </div>
      )}
      <div className="p-5">{children}</div>
    </div>
  )
}
