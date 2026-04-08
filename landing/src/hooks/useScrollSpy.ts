import { useState, useEffect, useCallback } from 'react'

export function useScrollSpy(sectionIds: string[], offset = 80): string {
  const [active, setActive] = useState<string>(sectionIds[0] ?? '')

  const handleScroll = useCallback(() => {
    const scrollY = window.scrollY + offset

    for (let i = sectionIds.length - 1; i >= 0; i--) {
      const id = sectionIds[i]
      const el = document.getElementById(id)
      if (el && el.offsetTop <= scrollY) {
        setActive(id)
        return
      }
    }
    setActive(sectionIds[0] ?? '')
  }, [sectionIds, offset])

  useEffect(() => {
    window.addEventListener('scroll', handleScroll, { passive: true })
    handleScroll()
    return () => window.removeEventListener('scroll', handleScroll)
  }, [handleScroll])

  return active
}
