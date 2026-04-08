import { useState, useCallback, useRef, createElement } from 'react'
import { Toast } from '@shared/ui'

interface ToastState {
  message: string
  type: 'success' | 'error'
  visible: boolean
}

export function useToast() {
  const [state, setState] = useState<ToastState>({ message: '', type: 'success', visible: false })
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const showToast = useCallback((message: string, type: 'success' | 'error', duration = 3000) => {
    if (timerRef.current) clearTimeout(timerRef.current)
    setState({ message, type, visible: true })
    timerRef.current = setTimeout(
      () => setState((s) => ({ ...s, visible: false })),
      duration,
    )
  }, [])

  const ToastComponent = state.visible
    ? createElement(Toast, { message: state.message, type: state.type })
    : null

  return { showToast, ToastComponent }
}
