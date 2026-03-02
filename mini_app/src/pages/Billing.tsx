import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { billingApi, PackageInfo } from '@/api/billing'
import { useInvoicePolling } from '@/hooks/useBilling'
import { Skeleton } from '@/components/ui/Skeleton'

// ─── Константы ──────────────────────────────────────────────────

const CURRENCIES = [
  { code: 'USDT', icon: '💵', name: 'Tether' },
  { code: 'TON',  icon: '💎', name: 'TON'    },
  { code: 'BTC',  icon: '₿',  name: 'Bitcoin' },
  { code: 'ETH',  icon: 'Ξ',  name: 'Ethereum'},
  { code: 'LTC',  icon: 'Ł',  name: 'Litecoin'},
]

const PLAN_INFO: Record<string, {
  emoji: string
  name: string
  color: string
  features: string[]
}> = {
  free:     { emoji: '🆓', name: 'FREE',     color: 'var(--neutral)',  features: ['Ознакомление', 'Без ИИ'] },
  starter:  { emoji: '🚀', name: 'STARTER',  color: 'var(--info)',     features: ['5 кампаний/мес', '50 чатов', '🦙 Llama 4 Scout'] },
  pro:      { emoji: '💎', name: 'PRO',      color: 'var(--accent-400)', features: ['20 кампаний/мес', '200 чатов', '✨ Claude Sonnet 4.6', '5 ИИ включено'] },
  business: { emoji: '🏢', name: 'BUSINESS', color: 'var(--warning)',  features: ['100 кампаний', '1000 чатов', '✨ Claude Sonnet 4.6', '20 ИИ включено'] },
}

// ─── Утилиты ────────────────────────────────────────────────────

function daysLeft(iso: string | null): number | null {
  if (!iso) return null
  return Math.max(0, Math.ceil((new Date(iso).getTime() - Date.now()) / 86_400_000))
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })
}

// ─── Компоненты ─────────────────────────────────────────────────

/** Карточка пакета кредитов */
function PackageCard({
  pkg, selected, onClick,
}: {
  pkg: PackageInfo
  selected: boolean
  onClick: () => void
}) {
  return (
    <motion.button
      onClick={onClick}
      whileTap={{ scale: 0.96 }}
      style={{
        border: `2px solid ${selected ? 'var(--accent-500)' : 'var(--border)'}`,
        borderRadius: 14,
        background: selected ? 'rgba(99,102,241,0.08)' : 'var(--bg-surface)',
        padding: '14px 12px',
        cursor: 'pointer',
        textAlign: 'left',
        width: '100%',
        transition: 'all 150ms',
        fontFamily: 'var(--font-body)',
      }}
    >
      {/* Название + бонус */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
        <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>
          {pkg.label}
        </span>
        {pkg.bonus > 0 && (
          <span style={{
            fontSize: 10, fontWeight: 700,
            background: 'var(--success-dim)', color: 'var(--success)',
            padding: '2px 6px', borderRadius: 4,
          }}>
            +{pkg.bonus} бонус
          </span>
        )}
      </div>

      {/* Кредиты */}
      <p className="font-mono" style={{ fontSize: 20, fontWeight: 700, lineHeight: 1, marginBottom: 4 }}>
        {pkg.total_credits.toLocaleString('ru')} кр
      </p>

      {/* Цена в USDT */}
      <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
        ≈ ${pkg.usdt_approx} USDT
      </p>
    </motion.button>
  )
}

/** Bottom sheet выбора криптовалюты */
function CurrencySheet({
  pkg, amounts, onSelect, onClose,
}: {
  pkg: PackageInfo | null
  amounts: Record<string, string>
  onSelect: (currency: string) => void
  onClose: () => void
}) {
  return (
    <AnimatePresence>
      {pkg && (
        <>
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={onClose}
            style={{
              position: 'fixed', inset: 0, zIndex: 102,
              background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(2px)',
            }}
          />
          <motion.div
            initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
            style={{
              position: 'fixed', bottom: 0, left: 0, right: 0, zIndex: 103,
              background: 'var(--bg-surface)',
              borderRadius: '20px 20px 0 0',
              padding: '0 20px calc(32px + env(safe-area-inset-bottom))',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'center', padding: '12px 0 8px' }}>
              <div style={{ width: 36, height: 4, background: 'var(--border)', borderRadius: 2 }} />
            </div>

            <h3 style={{ fontSize: 17, fontWeight: 700, marginBottom: 4 }}>
              Выберите валюту
            </h3>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 20 }}>
              {pkg.total_credits.toLocaleString('ru')} кредитов
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {CURRENCIES.map(({ code, icon, name }) => (
                <button
                  key={code}
                  className="btn"
                  onClick={() => onSelect(code)}
                  style={{
                    background: 'var(--bg-elevated)',
                    color: 'var(--text-primary)',
                    border: '1px solid var(--border)',
                    justifyContent: 'space-between',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{ fontSize: 20, width: 28 }}>{icon}</span>
                    <div style={{ textAlign: 'left' }}>
                      <div style={{ fontWeight: 600 }}>{code}</div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 400 }}>
                        {name}
                      </div>
                    </div>
                  </div>
                  <span className="font-mono" style={{ fontSize: 14, fontWeight: 600 }}>
                    {amounts[code] ?? '...'}
                  </span>
                </button>
              ))}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}

/** Статус инвойса после создания */
function InvoiceWaiting({
  invoiceId, payUrl, onClose,
}: {
  invoiceId: string
  payUrl: string
  onClose: () => void
}) {
  const invoiceStatus = useInvoicePolling(invoiceId)
  const isPaid    = invoiceStatus?.status === 'paid'
  const isExpired = invoiceStatus?.status === 'expired'

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        style={{
          position: 'fixed', inset: 0, zIndex: 200,
          background: 'rgba(8, 11, 18, 0.95)',
          display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center',
          padding: 24,
        }}
      >
        {isPaid ? (
          <>
            <motion.div
              initial={{ scale: 0 }} animate={{ scale: 1 }}
              transition={{ type: 'spring', damping: 12 }}
              style={{ fontSize: 72, marginBottom: 20 }}
            >
              ✅
            </motion.div>
            <h2 style={{ fontSize: 22, fontWeight: 700, marginBottom: 8, textAlign: 'center' }}>
              Оплачено!
            </h2>
            <p style={{ fontSize: 14, color: 'var(--text-muted)', marginBottom: 8 }}>
              +{invoiceStatus?.credits ?? 0} кредитов зачислено
            </p>
            <button className="btn btn-primary" onClick={onClose} style={{ marginTop: 24, maxWidth: 280 }}>
              Отлично!
            </button>
          </>
        ) : isExpired ? (
          <>
            <div style={{ fontSize: 56, marginBottom: 20 }}>⏱</div>
            <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>
              Инвойс истёк
            </h2>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 24 }}>
              Попробуйте ещё раз
            </p>
            <button className="btn btn-ghost" onClick={onClose} style={{ maxWidth: 280 }}>
              Закрыть
            </button>
          </>
        ) : (
          <>
            {/* Спиннер ожидания */}
            <div style={{ display: 'flex', gap: 10, marginBottom: 32 }}>
              {[0, 1, 2].map(i => (
                <motion.div
                  key={i}
                  style={{
                    width: 10, height: 10, borderRadius: '50%',
                    background: 'var(--accent-500)',
                  }}
                  animate={{ scale: [1, 0.5, 1], opacity: [1, 0.3, 1] }}
                  transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.2 }}
                />
              ))}
            </div>
            <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8, textAlign: 'center' }}>
              Ожидаем оплату
            </h2>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 32, textAlign: 'center' }}>
              Проверяем каждые 5 секунд...
            </p>
            <a
              href={payUrl}
              target="_blank"
              rel="noopener"
              className="btn btn-primary"
              style={{ textDecoration: 'none', maxWidth: 280, marginBottom: 12 }}
            >
              Открыть инвойс ↗
            </a>
            <button className="btn btn-ghost" onClick={onClose} style={{ maxWidth: 280 }}>
              Отмена
            </button>
          </>
        )}
      </motion.div>
    </AnimatePresence>
  )
}

// ─── Главная страница ────────────────────────────────────────────

export default function Billing() {
  const qc = useQueryClient()

  const [selectedPkg, setSelectedPkg] = useState<PackageInfo | null>(null)
  const [pkgForCrypto, setPkgForCrypto] = useState<PackageInfo | null>(null)
  const [activeInvoice, setActiveInvoice] = useState<{ id: string; url: string } | null>(null)
  const [cryptoAmounts, setCryptoAmounts] = useState<Record<string, string>>({})

  const { data: balance, isLoading } = useQuery({
    queryKey: ['billing', 'balance'],
    queryFn: billingApi.balance,
    staleTime: 30_000,
  })

  const { data: history } = useQuery({
    queryKey: ['billing', 'history'],
    queryFn: () => billingApi.history(1),
    staleTime: 60_000,
  })

  const cryptoMutation = useMutation({
    mutationFn: ({ pkgId, currency }: { pkgId: string; currency: string }) =>
      billingApi.createCryptoInvoice(pkgId, currency),
    onSuccess: (data) => {
      setPkgForCrypto(null)
      setSelectedPkg(null)
      setActiveInvoice({ id: data.invoice_id, url: data.pay_url })
    },
    onError: () => {
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('error')
    },
  })

  const starsMutation = useMutation({
    mutationFn: (pkgId: string) => billingApi.createStarsInvoice(pkgId),
    onSuccess: (data) => {
      setSelectedPkg(null)
      window.open(data.invoice_link, '_blank')
    },
  })

  const planMutation = useMutation({
    mutationFn: (plan: string) => billingApi.changePlan(plan),
    onSuccess: (data) => {
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success')
      qc.invalidateQueries({ queryKey: ['billing', 'balance'] })
      qc.invalidateQueries({ queryKey: ['analytics', 'summary'] })
      window.Telegram?.WebApp?.showAlert(data.message)
    },
    onError: (err: any) => {
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('error')
      const msg = err?.response?.data?.detail ?? 'Ошибка смены тарифа'
      window.Telegram?.WebApp?.showAlert(msg)
    },
  })

  // Считаем суммы для выбранного пакета
  const handleCryptoOpen = (pkg: PackageInfo) => {
    const total = pkg.total_credits
    const amounts: Record<string, string> = {
      USDT: `${pkg.usdt_approx} USDT`,
      TON:  `${(total / 400).toFixed(2)} TON`,
      BTC:  `${(total / 9_000_000).toFixed(6)} BTC`,
      ETH:  `${(total / 300_000).toFixed(4)} ETH`,
      LTC:  `${(total / 7_000).toFixed(3)} LTC`,
    }
    setCryptoAmounts(amounts)
    setPkgForCrypto(pkg)
    setSelectedPkg(null)
  }

  const handleChangePlan = (plan: string) => {
    if (!balance) return
    const currentPlan = balance.plan
    if (plan === currentPlan) return

    const cost = balance.plan_costs[plan] ?? 0
    if (cost > balance.credits && plan !== 'free') {
      window.Telegram?.WebApp?.showAlert(
        `Недостаточно кредитов. Нужно: ${cost} кр, есть: ${balance.credits} кр`
      )
      return
    }

    const planInfo = PLAN_INFO[plan]
    const msg = cost > 0
      ? `Перейти на ${planInfo.name} за ${cost} кр?`
      : `Перейти на FREE (тариф сбросится)?`

    window.Telegram?.WebApp?.showConfirm(msg, (ok: boolean) => {
      if (ok) planMutation.mutate(plan)
    })
  }

  if (isLoading) {
    return (
      <div className="page-content" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <Skeleton height={160} radius={20} />
        <Skeleton height={48} radius={12} />
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          {[...Array(4)].map((_, i) => <Skeleton key={i} height={100} radius={14} />)}
        </div>
        <Skeleton height={200} radius={14} />
      </div>
    )
  }

  const b = balance!
  const currentPlanInfo = PLAN_INFO[b.plan]
  const days = daysLeft(b.plan_expires_at)

  return (
    <div className="page-content page-enter">

      {/* Карточка баланса */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        style={{
          background: 'linear-gradient(135deg, #1a2035 0%, #0f1521 100%)',
          border: '1px solid var(--border-accent)',
          borderRadius: 20,
          padding: 22,
          marginBottom: 12,
          boxShadow: 'var(--shadow-glow)',
        }}
      >
        <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>Баланс</p>
        <p className="font-mono" style={{ fontSize: 34, fontWeight: 700, lineHeight: 1, marginBottom: 4 }}>
          {b.credits.toLocaleString('ru')} кр
        </p>
        <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 14 }}>
          ≈ ${Math.round(b.credits / 90)}
        </p>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <span style={{
            background: currentPlanInfo?.color + '22',
            color: currentPlanInfo?.color,
            padding: '3px 10px', borderRadius: 6,
            fontSize: 12, fontWeight: 700,
          }}>
            {currentPlanInfo?.emoji} {currentPlanInfo?.name}
          </span>
          {days !== null && (
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              {days > 0 ? `${days} дней` : 'Истёк'}
            </span>
          )}
          {b.ai_included > 0 && (
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              ИИ: {b.ai_generations_used}/{b.ai_included}
            </span>
          )}
        </div>
      </motion.div>

      {/* ── Пополнить ── */}
      <p style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-muted)', marginBottom: 10 }}>
        ПОПОЛНИТЬ КРЕДИТЫ
      </p>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 20 }}>
        {b.packages.map((pkg, i) => (
          <motion.div
            key={pkg.id}
            initial={{ opacity: 0, scale: 0.93 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: i * 0.05 }}
          >
            <PackageCard
              pkg={pkg}
              selected={selectedPkg?.id === pkg.id}
              onClick={() => {
                setSelectedPkg(selectedPkg?.id === pkg.id ? null : pkg)
                window.Telegram?.WebApp?.HapticFeedback?.selectionChanged()
              }}
            />
          </motion.div>
        ))}
      </div>

      {/* Кнопки способов оплаты при выбранном пакете */}
      <AnimatePresence>
        {selectedPkg && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            style={{ marginBottom: 20, overflow: 'hidden' }}
          >
            <div style={{ display: 'flex', gap: 10 }}>
              <button
                className="btn"
                onClick={() => handleCryptoOpen(selectedPkg)}
                style={{
                  flex: 1,
                  background: 'var(--bg-elevated)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border)',
                  gap: 8,
                }}
              >
                💎 Крипто
              </button>
              <button
                className="btn"
                onClick={() => starsMutation.mutate(selectedPkg.id)}
                disabled={starsMutation.isPending}
                style={{
                  flex: 1,
                  background: 'var(--bg-elevated)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border)',
                  gap: 8,
                }}
              >
                {starsMutation.isPending ? '...' : '⭐ Stars'}
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Тарифы ── */}
      <p style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-muted)', marginBottom: 10 }}>
        ТАРИФНЫЕ ПЛАНЫ
      </p>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 24 }}>
        {Object.entries(PLAN_INFO).map(([planKey, info], i) => {
          const cost = b.plan_costs[planKey] ?? 0
          const isActive = b.plan === planKey
          const canAfford = b.credits >= cost || cost === 0

          return (
            <motion.div
              key={planKey}
              className="card"
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              style={{
                border: isActive
                  ? `2px solid ${info.color}`
                  : '1px solid var(--border)',
                opacity: !isActive && !canAfford ? 0.6 : 1,
              }}
            >
              <div style={{
                display: 'flex', alignItems: 'center',
                justifyContent: 'space-between', marginBottom: 8,
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 18 }}>{info.emoji}</span>
                  <span style={{ fontSize: 15, fontWeight: 700 }}>{info.name}</span>
                  {isActive && (
                    <span style={{
                      fontSize: 10, fontWeight: 700, padding: '2px 6px',
                      background: info.color + '22', color: info.color,
                      borderRadius: 4,
                    }}>
                      АКТИВЕН
                    </span>
                  )}
                </div>
                <span className="font-mono" style={{ fontSize: 14, fontWeight: 700, color: info.color }}>
                  {cost === 0 ? 'Бесплатно' : `${cost} кр`}
                </span>
              </div>

              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 10 }}>
                {info.features.map(f => (
                  <span key={f} style={{
                    fontSize: 11, color: 'var(--text-muted)',
                    background: 'var(--bg-elevated)',
                    padding: '3px 8px', borderRadius: 6,
                  }}>
                    {f}
                  </span>
                ))}
              </div>

              {!isActive && (
                <button
                  className="btn"
                  onClick={() => handleChangePlan(planKey)}
                  disabled={planMutation.isPending}
                  style={{
                    height: 36,
                    background: canAfford ? info.color + '22' : 'var(--bg-elevated)',
                    color: canAfford ? info.color : 'var(--text-muted)',
                    border: `1px solid ${canAfford ? info.color + '44' : 'var(--border)'}`,
                    fontSize: 13,
                  }}
                >
                  {canAfford ? 'Перейти' : `Нужно ещё ${cost - b.credits} кр`}
                </button>
              )}
            </motion.div>
          )
        })}
      </div>

      {/* ── История ── */}
      <p style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-muted)', marginBottom: 10 }}>
        ИСТОРИЯ ПЛАТЕЖЕЙ
      </p>

      {!history?.items.length ? (
        <div className="card" style={{ textAlign: 'center', padding: 24 }}>
          <p style={{ fontSize: 24, marginBottom: 8 }}>💳</p>
          <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>Платежей ещё не было</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {history.items.map((p, i) => {
            const isPaid      = p.status === 'paid'
            const total = p.credits + p.bonus_credits
            const methodIcon  = p.method === 'stars' ? '⭐' : '💎'
            const currencyStr = p.method === 'stars' ? 'Stars' : (p.currency ?? 'USDT')

            return (
              <motion.div
                key={p.id}
                className="card"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: i * 0.04 }}
                style={{
                  display: 'flex', alignItems: 'center', gap: 12,
                  padding: '12px 14px',
                }}
              >
                <span style={{ fontSize: 18, flexShrink: 0 }}>{methodIcon}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{ fontSize: 13, fontWeight: 600 }}>
                    {currencyStr}
                    {p.bonus_credits > 0 && (
                      <span style={{ color: 'var(--success)', fontSize: 11, marginLeft: 6 }}>
                        +{p.bonus_credits} бонус
                      </span>
                    )}
                  </p>
                  <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    {fmtDate(p.created_at)}
                  </p>
                </div>
                <div style={{ textAlign: 'right', flexShrink: 0 }}>
                  <p className="font-mono" style={{
                    fontSize: 15, fontWeight: 700,
                    color: isPaid ? 'var(--success)' : 'var(--text-muted)',
                  }}>
                    {isPaid ? '+' : ''}{total.toLocaleString('ru')} кр
                  </p>
                  <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    {p.status === 'paid' ? 'Зачислено' :
                     p.status === 'pending' ? 'Ожидание' :
                     p.status === 'expired' ? 'Истёк' : 'Отменён'}
                  </p>
                </div>
              </motion.div>
            )
          })}
        </div>
      )}

      {/* Bottom sheets */}
      <CurrencySheet
        pkg={pkgForCrypto}
        amounts={cryptoAmounts}
        onSelect={(currency) => {
          if (!pkgForCrypto) return
          cryptoMutation.mutate({ pkgId: pkgForCrypto.id, currency })
        }}
        onClose={() => setPkgForCrypto(null)}
      />

      {/* Ожидание оплаты */}
      {activeInvoice && (
        <InvoiceWaiting
          invoiceId={activeInvoice.id}
          payUrl={activeInvoice.url}
          onClose={() => {
            setActiveInvoice(null)
            qc.invalidateQueries({ queryKey: ['billing', 'balance'] })
            qc.invalidateQueries({ queryKey: ['billing', 'history'] })
          }}
        />
      )}

    </div>
  )
}
