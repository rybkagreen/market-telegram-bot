interface ToastProps {
  message: string
  type: 'success' | 'error'
}

const typeClasses: Record<string, string> = {
  success: 'bg-success-muted border-success text-text-primary',
  error: 'bg-danger-muted border-danger text-text-primary',
}

const typeIcons: Record<string, string> = {
  success: '✅',
  error: '❌',
}

export function Toast({ message, type }: ToastProps) {
  return (
    <div
      className={`fixed bottom-4 right-4 z-50 max-w-sm px-4 py-3 rounded-md border shadow-lg
        ${typeClasses[type]}
        animate-[fadeInUp_0.2s_ease-out]`}
    >
      <div className="flex items-start gap-2">
        <span className="shrink-0">{typeIcons[type]}</span>
        <span className="text-sm">{message}</span>
      </div>
    </div>
  )
}
