/// <reference types="vite/client" />

interface Window {
  Telegram?: {
    WebApp: {
      ready(): void
      expand(): void
      close(): void
      initData: string
      initDataUnsafe: Record<string, any>
      colorScheme: 'dark' | 'light'
      themeParams: Record<string, string>
      onEvent(event: string, callback: () => void): void
      showAlert(message: string, callback?: () => void): void
      showConfirm(message: string, callback: (confirmed: boolean) => void): void
      HapticFeedback: {
        impactOccurred(style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft'): void
        notificationOccurred(type: 'success' | 'warning' | 'error'): void
        selectionChanged(): void
      }
      MainButton: {
        text: string
        isVisible: boolean
        isActive: boolean
        show(): void
        hide(): void
        enable(): void
        disable(): void
        onClick(callback: () => void): void
        offClick(callback: () => void): void
      }
      BackButton: {
        isVisible: boolean
        show(): void
        hide(): void
        onClick(callback: () => void): void
        offClick(callback: () => void): void
      }
    }
  }
}
