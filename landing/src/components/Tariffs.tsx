import { Check, ArrowRight } from 'lucide-react'
import { TARIFFS, PLATFORM_COMMISSION, BOT_URL } from '../lib/constants'

export default function Tariffs() {
  return (
    <section
      id="tariffs"
      className="py-20 lg:py-32 bg-white dark:bg-zinc-950"
      aria-labelledby="tariffs-heading"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Heading */}
        <div className="max-w-2xl mx-auto text-center mb-4">
          <h2
            id="tariffs-heading"
            className="mb-4"
            style={{
              fontFamily: 'var(--font-display)',
              fontWeight: 600,
              fontSize: '1.9375rem',
              color: 'var(--color-text-dark)',
              lineHeight: 1.2,
            }}
          >
            Тарифы
          </h2>
          <p
            style={{
              fontFamily: 'var(--font-ui)',
              fontSize: '1rem',
              color: 'var(--color-text-secondary)',
              lineHeight: 1.6,
            }}
          >
            Выберите план, подходящий для вашего масштаба.
          </p>
        </div>

        {/* Note */}
        <p
          className="text-center mb-12 text-sm"
          style={{
            fontFamily: 'var(--font-ui)',
            color: 'var(--color-text-muted)',
          }}
        >
          Комиссия платформы {PLATFORM_COMMISSION * 100}% · Оплата в рублях
        </p>

        {/* Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {TARIFFS.map((tariff) => {
            const isPro = tariff.id === 'pro'
            return (
              <div
                key={tariff.id}
                className="relative flex flex-col p-7 border"
                style={{
                  borderRadius: 'var(--radius-xl)',
                  borderColor: isPro ? 'var(--color-brand-blue)' : 'var(--color-border)',
                  boxShadow: isPro ? 'var(--shadow-brand)' : 'var(--shadow-card)',
                  background: 'var(--color-bg-primary)',
                }}
              >
                {/* Popular badge */}
                {isPro && (
                  <span
                    className="absolute -top-3.5 left-1/2 -translate-x-1/2 px-3 py-1 text-xs font-semibold text-white whitespace-nowrap"
                    style={{
                      fontFamily: 'var(--font-ui)',
                      background: 'var(--color-brand-blue)',
                      borderRadius: 'var(--radius-pill)',
                    }}
                  >
                    Популярный
                  </span>
                )}

                {/* Plan name */}
                <div
                  className="mb-4 font-semibold text-base"
                  style={{
                    fontFamily: 'var(--font-display)',
                    color: isPro ? 'var(--color-brand-blue)' : 'var(--color-text-dark)',
                  }}
                >
                  {tariff.displayName}
                </div>

                {/* Price */}
                <div className="mb-6">
                  {tariff.priceRub === 0 ? (
                    <span
                      className="text-3xl font-bold"
                      style={{
                        fontFamily: 'var(--font-display)',
                        color: 'var(--color-text-dark)',
                      }}
                    >
                      Бесплатно
                    </span>
                  ) : (
                    <div className="flex items-end gap-1">
                      <span
                        className="text-3xl font-bold"
                        style={{
                          fontFamily: 'var(--font-display)',
                          color: 'var(--color-text-dark)',
                        }}
                      >
                        {tariff.priceRub.toLocaleString('ru-RU')} ₽
                      </span>
                      <span
                        className="text-sm mb-1"
                        style={{ fontFamily: 'var(--font-ui)', color: 'var(--color-text-muted)' }}
                      >
                        /мес
                      </span>
                    </div>
                  )}
                </div>

                {/* Features */}
                <ul className="flex flex-col gap-2.5 mb-8 flex-1">
                  {tariff.features.map((feat) => (
                    <li
                      key={feat}
                      className="flex items-start gap-2 text-sm"
                      style={{
                        fontFamily: 'var(--font-ui)',
                        color: 'var(--color-text-secondary)',
                      }}
                    >
                      <Check
                        size={15}
                        className="shrink-0 mt-0.5"
                        style={{ color: 'var(--color-brand-blue)' }}
                        aria-hidden="true"
                      />
                      {feat}
                    </li>
                  ))}
                </ul>

                {/* CTA */}
                <a
                  href={BOT_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center justify-center gap-2 w-full py-2.5 text-sm font-semibold text-white dark:text-white transition-opacity hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
                  style={{
                    fontFamily: 'var(--font-ui)',
                    background: isPro ? 'var(--color-brand-blue)' : 'var(--color-bg-dark)',
                    color: '#fff',
                    borderRadius: 'var(--radius-sm)',
                  }}
                >
                  Начать
                  <ArrowRight size={14} aria-hidden="true" />
                </a>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
