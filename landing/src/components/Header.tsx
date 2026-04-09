import { useState, useEffect } from 'react'
import { Link } from 'react-router'
import { motion, AnimatePresence } from 'motion/react'
import { Menu, X, Sun, Moon } from 'lucide-react'
import { useScrollSpy } from '../hooks/useScrollSpy'
import { useTheme } from '../context/ThemeContext'
import { BOT_URL, PORTAL_URL } from '../lib/constants'

const NAV_ITEMS = [
  { label: 'Возможности', href: '#features' },
  { label: 'Как работает', href: '#how-it-works' },
  { label: 'Тарифы', href: '#tariffs' },
  { label: 'Соответствие', href: '#compliance' },
  { label: 'FAQ', href: '#faq' },
] as const

const SECTION_IDS = NAV_ITEMS.map(i => i.href.slice(1))

export default function Header() {
  const [scrolled, setScrolled] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const { theme, toggle } = useTheme()
  const activeSection = useScrollSpy(SECTION_IDS)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 16)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => {
    const onResize = () => { if (window.innerWidth >= 1024) setMobileOpen(false) }
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  const handleNavClick = (href: string) => {
    setMobileOpen(false)
    const el = document.getElementById(href.slice(1))
    if (el) {
      const top = el.getBoundingClientRect().top + window.scrollY - 80
      window.scrollTo({ top, behavior: 'smooth' })
    }
  }

  return (
    <header className={[
      'fixed top-0 left-0 right-0 z-50 transition-all duration-300 bg-white dark:bg-zinc-950',
      scrolled ? 'shadow-sm backdrop-blur-md dark:shadow-black/30' : '',
    ].join(' ')}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">

          {/* Logo */}
          <Link to="/" className="flex items-center shrink-0" aria-label="RekHarbor — на главную">
            <span
              className="text-xl font-semibold text-blue-600"
              style={{ fontFamily: 'var(--font-display)' }}
            >Rek</span>
            <span
              className="text-xl font-semibold text-gray-900 dark:text-zinc-100"
              style={{ fontFamily: 'var(--font-display)' }}
            >Harbor</span>
          </Link>

          {/* Desktop nav */}
          <nav className="hidden lg:flex items-center gap-1" aria-label="Основная навигация">
            {NAV_ITEMS.map(({ label, href }) => {
              const isActive = activeSection === href.slice(1)
              return (
                <button
                  key={href}
                  onClick={() => handleNavClick(href)}
                  className={[
                    'px-3 py-1.5 text-sm font-medium rounded-full transition-colors',
                    isActive
                      ? 'bg-black/5 text-gray-900 dark:bg-white/10 dark:text-zinc-100'
                      : 'text-gray-500 hover:text-gray-900 hover:bg-black/5 dark:text-gray-400 dark:hover:text-zinc-100 dark:hover:bg-white/10',
                  ].join(' ')}
                  aria-current={isActive ? 'location' : undefined}
                >
                  {label}
                </button>
              )
            })}
          </nav>

          {/* Desktop CTA */}
          <div className="hidden lg:flex items-center gap-2">
            <button
              onClick={toggle}
              className="p-2 rounded-lg text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 hover:bg-black/5 dark:hover:bg-white/10 transition-colors"
              aria-label={theme === 'dark' ? 'Переключить на светлую тему' : 'Переключить на тёмную тему'}
            >
              {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            <a
              href={PORTAL_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
            >
              Войти в портал
            </a>
            <a
              href={BOT_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="px-4 py-2 text-sm font-medium text-white bg-gray-900 rounded-lg hover:opacity-90 transition-opacity"
            >
              Открыть бот
            </a>
          </div>

          {/* Mobile hamburger */}
          <button
            className="lg:hidden p-2 rounded-lg text-gray-500 hover:text-gray-900 hover:bg-black/5 dark:text-gray-400 dark:hover:text-zinc-100 dark:hover:bg-white/10 transition-colors"
            onClick={() => setMobileOpen(v => !v)}
            aria-label={mobileOpen ? 'Закрыть меню' : 'Открыть меню'}
            aria-expanded={mobileOpen}
          >
            {mobileOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>

      {/* Mobile drawer */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            key="mobile-menu"
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.18 }}
            className="lg:hidden border-t border-gray-100 dark:border-white/10 bg-white dark:bg-zinc-950"
          >
            <nav className="max-w-7xl mx-auto px-4 py-4 flex flex-col gap-1">
              {NAV_ITEMS.map(({ label, href }) => (
                <button
                  key={href}
                  onClick={() => handleNavClick(href)}
                  className="text-left px-3 py-2.5 text-sm font-medium text-gray-500 hover:text-gray-900 hover:bg-black/5 dark:text-gray-400 dark:hover:text-zinc-100 dark:hover:bg-white/10 rounded-lg transition-colors"
                >
                  {label}
                </button>
              ))}
              <div className="flex flex-col gap-2 mt-3 pt-3 border-t border-gray-100 dark:border-white/10">
                <button
                  onClick={toggle}
                  className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-black/5 dark:hover:bg-white/10 rounded-lg transition-colors"
                >
                  {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
                  {theme === 'dark' ? 'Светлая тема' : 'Тёмная тема'}
                </button>
                <a
                  href={PORTAL_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-4 py-2.5 text-sm font-medium text-center text-gray-700 bg-gray-100 dark:text-zinc-200 dark:bg-zinc-800 rounded-lg"
                >
                  Войти в портал
                </a>
                <a
                  href={BOT_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-4 py-2.5 text-sm font-medium text-center text-white bg-gray-900 dark:bg-zinc-100 dark:text-zinc-900 rounded-lg"
                >
                  Открыть бот
                </a>
              </div>
            </nav>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  )
}
