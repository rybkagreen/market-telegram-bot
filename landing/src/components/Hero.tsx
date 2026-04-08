import { useRef } from 'react'
import { motion, useReducedMotion } from 'motion/react'
import { ArrowRight, ShieldCheck, Zap, TrendingUp } from 'lucide-react'
import { BOT_URL, PORTAL_URL, PLATFORM_COMMISSION } from '../lib/constants'

const STATS = [
  { icon: ShieldCheck, value: 'Эскроу', label: 'защита каждой сделки', color: 'var(--color-brand-blue)' },
  { icon: Zap, value: `${(1 - PLATFORM_COMMISSION) * 100}%`, label: 'выплата владельцам', color: 'var(--color-brand-blue)' },
  { icon: TrendingUp, value: 'ОРД', label: 'регистрация автоматически', color: 'var(--color-brand-blue)' },
] as const

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0 },
}

export default function Hero() {
  const shouldReduceMotion = useReducedMotion()
  const sectionRef = useRef<HTMLElement>(null)

  const containerVariants = {
    hidden: {},
    visible: {
      transition: {
        staggerChildren: shouldReduceMotion ? 0 : 0.12,
      },
    },
  }

  const itemVariants = shouldReduceMotion
    ? { hidden: { opacity: 1, y: 0 }, visible: { opacity: 1, y: 0 } }
    : { ...fadeUp, transition: { duration: 0.5, ease: [0.25, 0.1, 0.25, 1] } }

  return (
    <section
      id="hero"
      ref={sectionRef}
      className="relative min-h-screen flex items-center bg-white pt-16"
      aria-label="Главный экран"
    >
      {/* Subtle background gradient — decorative */}
      <div
        className="absolute inset-0 pointer-events-none"
        aria-hidden="true"
        style={{
          background: 'radial-gradient(ellipse 80% 50% at 50% -10%, rgba(20,86,240,0.06) 0%, transparent 70%)',
        }}
      />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 lg:py-32">
        <motion.div
          className="max-w-4xl mx-auto text-center"
          variants={containerVariants}
          initial="hidden"
          animate="visible"
        >
          {/* Badge */}
          <motion.div variants={itemVariants} className="flex justify-center mb-6">
            <span
              className="inline-flex items-center gap-1.5 px-4 py-1.5 text-sm font-medium border"
              style={{
                fontFamily: 'var(--font-ui)',
                color: 'var(--color-brand-blue)',
                borderColor: 'rgba(20,86,240,0.2)',
                background: 'rgba(20,86,240,0.05)',
                borderRadius: 'var(--radius-pill)',
              }}
            >
              <ShieldCheck size={14} />
              Биржа рекламы с защитой эскроу
            </span>
          </motion.div>

          {/* H1 */}
          <motion.h1
            variants={itemVariants}
            className="mb-6"
            style={{
              fontFamily: 'var(--font-display)',
              fontWeight: 500,
              lineHeight: 1.1,
              color: 'var(--color-text-primary)',
              fontSize: 'clamp(2.5rem, 6vw, 5rem)',
            }}
          >
            Реклама в Telegram
            <br />
            <span style={{ color: 'var(--color-brand-blue)' }}>без рисков и лишних слов</span>
          </motion.h1>

          {/* Subtitle */}
          <motion.p
            variants={itemVariants}
            className="mb-10 max-w-2xl mx-auto"
            style={{
              fontFamily: 'var(--font-ui)',
              fontSize: 'clamp(1rem, 2vw, 1.25rem)',
              fontWeight: 400,
              lineHeight: 1.5,
              color: 'var(--color-text-secondary)',
            }}
          >
            Покупайте размещения в Telegram-каналах с автоматической регистрацией в ОРД,
            защитой эскроу и мгновенными выплатами владельцам. Весь процесс — через бот.
          </motion.p>

          {/* CTA buttons */}
          <motion.div
            variants={itemVariants}
            className="flex flex-col sm:flex-row items-center justify-center gap-3 mb-16"
          >
            <a
              href={BOT_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-6 py-3 text-sm font-semibold text-white transition-opacity hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
              style={{
                fontFamily: 'var(--font-ui)',
                background: 'var(--color-bg-dark)',
                borderRadius: 'var(--radius-sm)',
              }}
            >
              Начать в Telegram
              <ArrowRight size={16} />
            </a>
            <a
              href={PORTAL_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-6 py-3 text-sm font-semibold transition-colors hover:bg-black/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
              style={{
                fontFamily: 'var(--font-ui)',
                background: 'var(--color-bg-light)',
                color: '#333333',
                borderRadius: 'var(--radius-sm)',
              }}
            >
              Открыть портал
            </a>
          </motion.div>

          {/* Stats */}
          <motion.div
            variants={itemVariants}
            className="grid grid-cols-1 sm:grid-cols-3 gap-4"
          >
            {STATS.map(({ icon: Icon, value, label, color }) => (
              <div
                key={label}
                className="flex flex-col items-center gap-2 p-6 border transition-shadow hover:shadow-[var(--shadow-brand)]"
                style={{
                  borderRadius: 'var(--radius-lg)',
                  borderColor: 'var(--color-border)',
                  background: '#fff',
                  boxShadow: 'var(--shadow-card)',
                }}
              >
                <Icon size={28} style={{ color }} aria-hidden="true" />
                <span
                  className="text-2xl font-semibold"
                  style={{ fontFamily: 'var(--font-display)', color: 'var(--color-text-dark)' }}
                >
                  {value}
                </span>
                <span
                  className="text-sm text-center"
                  style={{ fontFamily: 'var(--font-ui)', color: 'var(--color-text-muted)' }}
                >
                  {label}
                </span>
              </div>
            ))}
          </motion.div>
        </motion.div>
      </div>
    </section>
  )
}
