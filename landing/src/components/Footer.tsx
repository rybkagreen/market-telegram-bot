import { Link } from 'react-router'
import { BOT_URL, PORTAL_URL } from '../lib/constants'

const FOOTER_LINKS = {
  product: [
    { label: 'Как работает', href: '#how-it-works' },
    { label: 'Тарифы', href: '#tariffs' },
    { label: 'Для рекламодателей', href: `${BOT_URL}?start=advertiser` },
    { label: 'Для владельцев каналов', href: `${BOT_URL}?start=owner` },
  ],
  company: [
    { label: 'О платформе', href: '#features' },
    { label: 'ОРД и маркировка', href: '#compliance' },
    { label: 'FAQ', href: '#faq' },
    { label: 'Политика конфиденциальности', href: '/privacy', isInternal: true },
  ],
  contacts: [
    { label: 'Telegram-бот', href: BOT_URL },
    { label: 'Веб-портал', href: PORTAL_URL },
  ],
} as const

function FooterLink({
  href,
  label,
  isInternal = false,
}: {
  href: string
  label: string
  isInternal?: boolean
}) {
  const cls = 'text-sm transition-colors hover:text-white focus-visible:text-white'
  const style = { fontFamily: 'var(--font-ui)', color: 'rgba(255,255,255,0.7)' }

  if (isInternal) {
    return (
      <Link to={href} className={cls} style={style}>
        {label}
      </Link>
    )
  }

  const isAnchor = href.startsWith('#')
  return (
    <a
      href={href}
      className={cls}
      style={style}
      {...(!isAnchor && { target: '_blank', rel: 'noopener noreferrer' })}
    >
      {label}
    </a>
  )
}

export default function Footer() {
  const year = new Date().getFullYear()

  return (
    <footer
      style={{ background: 'var(--color-bg-dark)', fontFamily: 'var(--font-ui)' }}
      aria-label="Подвал сайта"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-10 mb-12">

          {/* Brand column */}
          <div className="sm:col-span-2 lg:col-span-1">
            <Link
              to="/"
              className="inline-flex items-baseline gap-0.5 mb-4"
              aria-label="RekHarbor — на главную"
              style={{ fontFamily: 'var(--font-display)' }}
            >
              <span className="text-xl font-semibold" style={{ color: 'var(--color-brand-blue-light)' }}>
                Rek
              </span>
              <span className="text-xl font-semibold text-white">Harbor</span>
            </Link>
            <p
              className="text-sm leading-relaxed max-w-xs"
              style={{ color: 'rgba(255,255,255,0.55)' }}
            >
              Рекламная биржа для Telegram-каналов с защитой эскроу, авторегистрацией в ОРД
              и автоматическими выплатами.
            </p>
          </div>

          {/* Product */}
          <div>
            <h3
              className="text-xs font-semibold uppercase tracking-wider mb-4"
              style={{ color: 'rgba(255,255,255,0.4)' }}
            >
              Продукт
            </h3>
            <ul className="flex flex-col gap-2.5">
              {FOOTER_LINKS.product.map(link => (
                <li key={link.label}>
                  <FooterLink {...link} />
                </li>
              ))}
            </ul>
          </div>

          {/* Company */}
          <div>
            <h3
              className="text-xs font-semibold uppercase tracking-wider mb-4"
              style={{ color: 'rgba(255,255,255,0.4)' }}
            >
              Компания
            </h3>
            <ul className="flex flex-col gap-2.5">
              {FOOTER_LINKS.company.map(link => (
                <li key={link.label}>
                  <FooterLink {...(link as { href: string; label: string; isInternal?: boolean })} />
                </li>
              ))}
            </ul>
          </div>

          {/* Contacts */}
          <div>
            <h3
              className="text-xs font-semibold uppercase tracking-wider mb-4"
              style={{ color: 'rgba(255,255,255,0.4)' }}
            >
              Контакты
            </h3>
            <ul className="flex flex-col gap-2.5">
              {FOOTER_LINKS.contacts.map(link => (
                <li key={link.label}>
                  <FooterLink {...link} />
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Divider */}
        <div className="border-t" style={{ borderColor: 'rgba(255,255,255,0.1)' }} />

        {/* Bottom row: legal */}
        <div className="pt-8 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <p className="text-xs" style={{ color: 'rgba(255,255,255,0.35)' }}>
            © {year} ООО «АЛГОРИТМИК АРТС». Все права защищены.
          </p>
          <p className="text-xs" style={{ color: 'rgba(255,255,255,0.35)' }}>
            Товарный знак RekHarbor (РекХарбор).{' '}
            <Link
              to="/privacy"
              className="underline underline-offset-2 hover:text-white transition-colors"
              style={{ color: 'rgba(255,255,255,0.45)' }}
            >
              Политика конфиденциальности
            </Link>
          </p>
        </div>
      </div>
    </footer>
  )
}
