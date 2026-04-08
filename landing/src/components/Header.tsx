import { useState, useEffect } from 'react'
import { Link } from 'react-router'
import { motion, AnimatePresence } from 'motion/react'
import { Menu, X } from 'lucide-react'
import { useScrollSpy } from '../hooks/useScrollSpy'
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
    <header
      className={[
        'fixed top-0 left-0 right-0 z-50 transition-all duration-300',
        scrolled
          ? 'bg-white/95 backdrop-blur-md shadow-[var(--shadow-card)]'
          : 'bg-white',
      ].join(' ')}
      style={{ fontFamily: 'var(--font-ui)' }}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">

          {/* Logo */}
          <Link
            to="/"
            className="flex items-center gap-2 shrink-0"
            style={{ fontFamily: 'var(--font-display)' }}
            aria-label="RekHarbor — на главную"
          >
            <span className="text-xl font-semibold" style={{ color: 'var(--color-brand-blue)' }}>
              Rek
            </span>
            <span className="text-xl font-semibold" style={{ color: 'var(--color-text-dark)' }}>
              Harbor
            </span>
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
                    'px-3 py-1.5 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-black/5 text-[#18181b]'
                      : 'text-[#45515e] hover:text-[#18181b] hover:bg-black/5',
                  ].join(' ')}
                  style={{ borderRadius: 'var(--radius-pill)' }}
                  aria-current={isActive ? 'location' : undefined}
                >
                  {label}
                </button>
              )
            })}
          </nav>

          {/* Desktop CTA */}
          <div className="hidden lg:flex items-center gap-2">
            <a
              href={PORTAL_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="px-4 py-2 text-sm font-medium rounded-lg transition-colors hover:opacity-80"
              style={{
                background: 'var(--color-bg-light)',
                color: '#333333',
                borderRadius: 'var(--radius-sm)',
              }}
            >
              Войти в портал
            </a>
            <a
              href={BOT_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="px-4 py-2 text-sm font-medium text-white rounded-lg transition-opacity hover:opacity-90"
              style={{
                background: 'var(--color-bg-dark)',
                borderRadius: 'var(--radius-sm)',
              }}
            >
              Открыть бот
            </a>
          </div>

          {/* Mobile hamburger */}
          <button
            className="lg:hidden p-2 rounded-lg text-[#45515e] hover:text-[#18181b] hover:bg-black/5 transition-colors"
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
            transition={{ duration: 0.18, ease: 'easeOut' }}
            className="lg:hidden border-t bg-white"
            style={{ borderColor: 'var(--color-border)' }}
          >
            <nav
              className="max-w-7xl mx-auto px-4 py-4 flex flex-col gap-1"
              aria-label="Мобильная навигация"
            >
              {NAV_ITEMS.map(({ label, href }) => (
                <button
                  key={href}
                  onClick={() => handleNavClick(href)}
                  className="text-left px-3 py-2.5 text-sm font-medium text-[#45515e] hover:text-[#18181b] hover:bg-black/5 rounded-lg transition-colors"
                >
                  {label}
                </button>
              ))}
              <div
                className="flex flex-col gap-2 mt-3 pt-3 border-t"
                style={{ borderColor: 'var(--color-border-subtle)' }}
              >
                <a
                  href={PORTAL_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-4 py-2.5 text-sm font-medium text-center rounded-lg transition-colors hover:opacity-80"
                  style={{
                    background: 'var(--color-bg-light)',
                    color: '#333333',
                    borderRadius: 'var(--radius-sm)',
                  }}
                >
                  Войти в портал
                </a>
                <a
                  href={BOT_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-4 py-2.5 text-sm font-medium text-center text-white rounded-lg transition-opacity hover:opacity-90"
                  style={{
                    background: 'var(--color-bg-dark)',
                    borderRadius: 'var(--radius-sm)',
                  }}
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
