import { useState } from 'react'

const CONSENT_KEY = 'rh_cookie_consent'

export type ConsentState = 'pending' | 'accepted' | 'declined'

export function useConsent() {
  const [consent, setConsent] = useState<ConsentState>(() => {
    if (typeof window === 'undefined') return 'pending'
    const stored = localStorage.getItem(CONSENT_KEY)
    if (stored === 'accepted' || stored === 'declined') return stored
    return 'pending'
  })

  const accept = () => {
    localStorage.setItem(CONSENT_KEY, 'accepted')
    setConsent('accepted')
  }

  const decline = () => {
    localStorage.setItem(CONSENT_KEY, 'declined')
    setConsent('declined')
  }

  return { consent, accept, decline }
}
