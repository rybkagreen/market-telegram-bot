// ============================================================
// RekHarbor Mini App — useHaptic hook
// Phase 3 | Shortcut haptic feedback actions
// ============================================================

import { useTelegram } from './useTelegram'

export function useHaptic() {
  const { hapticImpact, hapticNotification, hapticSelection } = useTelegram()

  return {
    tap:     () => hapticImpact('light'),
    success: () => hapticNotification('success'),
    error:   () => hapticNotification('error'),
    warning: () => hapticNotification('warning'),
    select:  () => hapticSelection(),
  }
}
