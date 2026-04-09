import { useRef } from 'react'
import { motion, useReducedMotion } from 'motion/react'
import type { Variants } from 'motion/react'
import { ArrowRight, ShieldCheck, Zap, TrendingUp } from 'lucide-react'
import { BOT_URL, PORTAL_URL, PLATFORM_COMMISSION } from '../lib/constants'

const STATS = [
  { icon: ShieldCheck, value: 'Эскроу', label: 'защита каждой сделки' },
  { icon: Zap, value: `${Math.round((1 - PLATFORM_COMMISSION) * 100)}%`, label: 'выплата владельцам' },
  { icon: TrendingUp, value: 'ОРД', label: 'регистрация автоматически' },
]

export default function Hero() {
  const shouldReduceMotion = useReducedMotion()
  const sectionRef = useRef<HTMLElement>(null)

  const containerVariants: Variants = {
    hidden: {},
    visible: shouldReduceMotion ? {} : { transition: { staggerChildren: 0.12 } },
  }

  const itemVariants: Variants = shouldReduceMotion
    ? { hidden: { opacity: 1, y: 0 }, visible: { opacity: 1, y: 0 } }
    : { hidden: { opacity: 0, y: 24 }, visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.25, 0.1, 0.25, 1] } } }

  return (
    <section
      id="hero"
      ref={sectionRef}
      className="relative min-h-screen flex items-center bg-white dark:bg-zinc-950 pt-16"
    >
      {/* Декоративный градиент */}
      <div
        className="absolute inset-0 pointer-events-none"
        aria-hidden="true"
        style={{
          background: 'radial-gradient(ellipse 80% 50% at 50% -10%, rgba(20,86,240,0.06) 0%, transparent 70%)',
        }}
      />
      {/* Декоративный градиент — dark */}
      <div
        className="absolute inset-0 pointer-events-none hidden dark:block"
        aria-hidden="true"
        style={{
          background: 'radial-gradient(ellipse 80% 50% at 50% -10%, rgba(20,86,240,0.12) 0%, transparent 70%)',
        }}
      />

      <div className="relative w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 lg:py-32">
        <motion.div
          className="max-w-4xl mx-auto text-center"
          animate="visible"
          initial="hidden"
          variants={containerVariants}
        >
          {/* Badge */}
          <motion.div
            variants={itemVariants}
            className="flex justify-center mb-6"
          >
            <span className="inline-flex items-center gap-1.5 px-4 py-1.5 text-sm font-medium rounded-full border border-blue-200 bg-blue-50 text-blue-600 dark:border-blue-900 dark:bg-blue-950/50 dark:text-blue-400">
              <ShieldCheck size={14} />
              Биржа рекламы с защитой эскроу
            </span>
          </motion.div>

          {/* H1 */}
          <motion.h1
            variants={itemVariants}
            className="mb-6 text-5xl sm:text-6xl lg:text-7xl font-medium leading-tight tracking-tight text-gray-900 dark:text-zinc-50"
            style={{ fontFamily: 'var(--font-display)' }}
          >
            Реклама в Telegram
            <br />
            <span className="text-blue-600 dark:text-blue-400">без рисков и лишних слов</span>
          </motion.h1>

          {/* Subtitle */}
          <motion.p
            variants={itemVariants}
            className="mb-10 max-w-2xl mx-auto text-lg sm:text-xl text-gray-500 dark:text-zinc-400 leading-relaxed"
          >
            Покупайте размещения в Telegram-каналах с автоматической регистрацией в ОРД,
            защитой эскроу и мгновенными выплатами владельцам. Весь процесс — через бот.
          </motion.p>

          {/* CTA */}
          <motion.div
            variants={itemVariants}
            className="flex flex-col sm:flex-row items-center justify-center gap-3 mb-16"
          >
            <a
              href={BOT_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-6 py-3 text-sm font-semibold text-white bg-gray-900 dark:bg-zinc-100 dark:text-zinc-900 rounded-lg hover:opacity-90 transition-opacity"
            >
              Начать в Telegram
              <ArrowRight size={16} />
            </a>
            <a
              href={PORTAL_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-6 py-3 text-sm font-semibold text-gray-700 bg-gray-100 dark:text-zinc-200 dark:bg-zinc-800 rounded-lg hover:bg-gray-200 dark:hover:bg-zinc-700 transition-colors"
            >
              Открыть портал
            </a>
          </motion.div>

          {/* Stats */}
          <motion.div
            variants={itemVariants}
            className="grid grid-cols-1 sm:grid-cols-3 gap-4"
          >
            {STATS.map(({ icon: Icon, value, label }) => (
              <div
                key={label}
                className="flex flex-col items-center gap-2 p-6 bg-white dark:bg-zinc-900 rounded-2xl border border-gray-200 dark:border-zinc-800 shadow-sm dark:shadow-none hover:shadow-md transition-shadow"
              >
                <Icon size={28} className="text-blue-600 dark:text-blue-400" aria-hidden="true" />
                <span
                  className="text-2xl font-semibold text-gray-900 dark:text-zinc-100"
                  style={{ fontFamily: 'var(--font-display)' }}
                >
                  {value}
                </span>
                <span className="text-sm text-center text-gray-500 dark:text-zinc-500">
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
