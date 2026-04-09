import { createContext, useContext, useEffect, useState, useCallback } from 'react'

type Theme = 'light' | 'dark'

interface ThemeContextValue {
  theme: Theme
  toggle: () => void
}

const ThemeContext = createContext<ThemeContextValue>({
  theme: 'light',
  toggle: () => {},
})

function getInitialTheme(): Theme {
  try {
    const stored = localStorage.getItem('rekharbor-theme')
    if (stored === 'dark' || stored === 'light') return stored
  } catch { /* noop */ }
  // Fallback to system preference
  if (typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return 'dark'
  }
  return 'light'
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<Theme>(getInitialTheme)

  // Listen for system theme changes (only when user hasn't manually toggled)
  useEffect(() => {
    const hasManualPreference = (() => {
      try { return localStorage.getItem('rekharbor-theme') !== null } catch { return false }
    })()
    if (hasManualPreference) return // user chose explicitly — don't follow system

    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const handler = (e: MediaQueryListEvent) => {
      setTheme(e.matches ? 'dark' : 'light')
    }
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [])

  useEffect(() => {
    const root = document.documentElement
    if (theme === 'dark') {
      root.classList.add('dark')
    } else {
      root.classList.remove('dark')
    }
    try { localStorage.setItem('rekharbor-theme', theme) } catch { /* noop */ }
  }, [theme])

  const toggle = useCallback(() => setTheme(prev => (prev === 'light' ? 'dark' : 'light')), [])

  return (
    <ThemeContext.Provider value={{ theme, toggle }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  return useContext(ThemeContext)
}
