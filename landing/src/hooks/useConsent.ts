import { useState, useEffect } from 'react'

const CONSENT_KEY = 'rh_cookie_consent'

export type ConsentState = 'pending' | 'accepted' | 'declined'

export function useConsent() {
  const [consent, setConsent] = useState<ConsentState>('pending')

  useEffect(() => {
    const stored = localStorage.getItem(CONSENT_KEY) as ConsentState | null
    if (stored === 'accepted' || stored === 'declined') {
      setConsent(stored)
    }
  }, [])

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
