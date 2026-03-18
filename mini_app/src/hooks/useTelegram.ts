// ============================================================
// RekHarbor Mini App — useTelegram hook
// Phase 3 | Wrapper over window.Telegram.WebApp
// ============================================================

import { useMemo, useCallback } from 'react'

export function useTelegram() {
  const tg = useMemo(() => window.Telegram?.WebApp, [])

  const user = tg?.initDataUnsafe?.user
  const initData = tg?.initData ?? ''
  const colorScheme = tg?.colorScheme ?? 'dark'

  const hapticImpact = useCallback(
    (style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft') => {
      tg?.HapticFeedback.impactOccurred(style)
    },
    [tg],
  )

  const hapticNotification = useCallback(
    (type: 'error' | 'success' | 'warning') => {
      tg?.HapticFeedback.notificationOccurred(type)
    },
    [tg],
  )

  const hapticSelection = useCallback(() => {
    tg?.HapticFeedback.selectionChanged()
  }, [tg])

  const showMainButton = useCallback(
    (text: string, onClick: () => void) => {
      if (!tg) return
      tg.MainButton.offClick(onClick)
      tg.MainButton.setText(text)
      tg.MainButton.onClick(onClick)
      tg.MainButton.show()
    },
    [tg],
  )

  const hideMainButton = useCallback(
    (onClick?: () => void) => {
      if (!tg) return
      if (onClick) tg.MainButton.offClick(onClick)
      tg.MainButton.hide()
    },
    [tg],
  )

  const close = useCallback(() => {
    tg?.close()
  }, [tg])

  return {
    tg,
    user,
    initData,
    colorScheme,
    hapticImpact,
    hapticNotification,
    hapticSelection,
    showMainButton,
    hideMainButton,
    close,
  }
}
