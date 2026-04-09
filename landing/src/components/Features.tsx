import { motion } from 'motion/react'
import {
  ShieldCheck,
  FileCheck,
  Sparkles,
  Star,
  Eye,
  ArrowLeftRight,
} from 'lucide-react'

const FEATURES = [
  {
    icon: ShieldCheck,
    title: 'Эскроу-защита',
    description:
      'Деньги резервируются на платформе до публикации. Владелец получает выплату только после подтверждения размещения. Нет публикации — возврат 100%.',
  },
  {
    icon: FileCheck,
    title: 'Авторегистрация в ОРД',
    description:
      'Каждое размещение автоматически регистрируется в Яндекс ОРД (API v7), получает erid-токен и маркировку перед публикацией. Соответствие закону без ваших усилий.',
  },
  {
    icon: Sparkles,
    title: 'AI-генерация текстов',
    description:
      'Mistral AI создаёт рекламный текст на основе описания вашего продукта. Встроенная модерация отсеивает запрещённый контент автоматически.',
  },
  {
    icon: Star,
    title: 'Система репутации',
    description:
      'Рейтинг 0.0–10.0 для каждого участника. Нарушения снижают рейтинг, 30 дней безупречной работы восстанавливают его. При критическом уровне — временная блокировка.',
  },
  {
    icon: Eye,
    title: 'Мониторинг публикаций',
    description:
      'Бот автоматически проверяет, что пост опубликован и остаётся в канале на протяжении всего срока размещения. Нарушения фиксируются без участия рекламодателя.',
  },
  {
    icon: ArrowLeftRight,
    title: 'Торг по цене',
    description:
      'Владелец канала может принять заявку, отклонить или предложить другую цену. До 3 раундов переговоров с автоматическим закрытием при истечении времени.',
  },
] as const

const containerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.08 } },
}

const cardVariants = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.45, ease: [0.25, 0.1, 0.25, 1] as const } },
}

export default function Features() {
  return (
    <section
      id="features"
      className="py-20 lg:py-32 bg-white dark:bg-zinc-950"
      aria-labelledby="features-heading"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Heading */}
        <div className="max-w-2xl mx-auto text-center mb-14">
          <h2
            id="features-heading"
            className="mb-4"
            style={{
              fontFamily: 'var(--font-display)',
              fontWeight: 600,
              fontSize: '1.9375rem',
              color: 'var(--color-text-dark)',
              lineHeight: 1.2,
            }}
          >
            Всё, что нужно для безопасной рекламы
          </h2>
          <p
            style={{
              fontFamily: 'var(--font-ui)',
              fontSize: '1rem',
              color: 'var(--color-text-secondary)',
              lineHeight: 1.6,
            }}
          >
            Платформа автоматизирует весь цикл — от создания заявки до получения выплаты,
            соблюдая требования закона о рекламе.
          </p>
        </div>

        {/* Cards grid */}
        <motion.div
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6"
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: '-60px' }}
        >
          {FEATURES.map(({ icon: Icon, title, description }) => (
            <motion.div
              key={title}
              variants={cardVariants}
              className="flex flex-col gap-4 p-6 border transition-shadow hover:shadow-[var(--shadow-brand)]"
              style={{
                borderRadius: 'var(--radius-md)',
                borderColor: 'var(--color-border)',
                background: 'var(--color-bg-primary)',
                boxShadow: 'var(--shadow-card)',
              }}
            >
              <div
                className="inline-flex items-center justify-center w-11 h-11 shrink-0"
                style={{
                  background: 'rgba(20,86,240,0.08)',
                  borderRadius: 'var(--radius-sm)',
                }}
              >
                <Icon size={22} style={{ color: 'var(--color-brand-blue)' }} aria-hidden="true" />
              </div>
              <div>
                <h3
                  className="mb-1.5 font-semibold"
                  style={{
                    fontFamily: 'var(--font-display)',
                    fontSize: '1rem',
                    color: 'var(--color-text-dark)',
                  }}
                >
                  {title}
                </h3>
                <p
                  style={{
                    fontFamily: 'var(--font-ui)',
                    fontSize: '0.875rem',
                    color: 'var(--color-text-secondary)',
                    lineHeight: 1.6,
                  }}
                >
                  {description}
                </p>
              </div>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  )
}
