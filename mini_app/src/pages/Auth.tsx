import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { authApi } from '@/api/auth'
import { useAuthStore } from '@/store/authStore'

interface Props {
  onSuccess: () => void
}

export default function Auth({ onSuccess }: Props) {
  const setAuth = useAuthStore((s) => s.setAuth)
  const [error, setError] = useState<string | null>(null)
  const [status, setStatus] = useState<'loading' | 'error'>('loading')

  useEffect(() => {
    const tg = window.Telegram?.WebApp
    if (!tg) {
      setError('Открой в Telegram')
      setStatus('error')
      return
    }

    tg.ready()
    tg.expand()

    const initData = tg.initData
    if (!initData) {
      // В режиме разработки вне Telegram — показываем ошибку
      if (import.meta.env.DEV) {
        console.warn('DEV MODE: No initData, using mock auth')
        setError('DEV: открой через Telegram или настрой тестовый токен')
        setStatus('error')
        return
      }
      setError('Не удалось получить данные Telegram')
      setStatus('error')
      return
    }

    authApi.login(initData)
      .then(({ access_token, user }) => {
        setAuth(access_token, user)
        onSuccess()
      })
      .catch((err) => {
        console.error('Auth error:', err)
        const msg = err.response?.data?.detail || 'Ошибка авторизации'
        setError(msg)
        setStatus('error')
      })
  }, [setAuth, onSuccess])

  return (
    <div
      style={{
        minHeight: '100dvh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
        background: 'var(--bg-base)',
      }}
    >
      {/* Логотип */}
      <motion.div
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.4, ease: 'backOut' }}
        style={{
          width: 72,
          height: 72,
          borderRadius: 20,
          background: 'linear-gradient(135deg, var(--accent-500), #8B5CF6)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 32,
          marginBottom: 20,
          boxShadow: 'var(--shadow-glow)',
        }}
      >
        📡
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
        style={{ textAlign: 'center' }}
      >
        <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 6 }}>
          Market Bot
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: 14, marginBottom: 32 }}>
          Рекламная платформа
        </p>

        {status === 'loading' && (
          <>
            <Spinner />
            <p style={{ color: 'var(--text-muted)', fontSize: 13, marginTop: 16 }}>
              Авторизация через Telegram...
            </p>
          </>
        )}

        {status === 'error' && (
          <>
            <p style={{
              color: 'var(--danger)',
              fontSize: 14,
              marginBottom: 20,
              padding: '12px 16px',
              background: 'var(--danger-dim)',
              borderRadius: 'var(--radius-md)',
            }}>
              {error}
            </p>
            <p style={{
              fontSize: 12,
              color: 'var(--text-muted)',
              marginBottom: 16,
            }}>
              Mini App работает только внутри Telegram.<br/>
              Откройте через бота @Eliza_rybka_assistant_bot
            </p>
            <a
              href="https://t.me/Eliza_rybka_assistant_bot"
              target="_blank"
              rel="noopener"
              className="btn btn-primary"
              style={{ textDecoration: 'none', maxWidth: 280 }}
            >
              Открыть в Telegram
            </a>
          </>
        )}
      </motion.div>
    </div>
  )
}

function Spinner() {
  return (
    <div style={{ display: 'flex', gap: 8, justifyContent: 'center' }}>
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          style={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: 'var(--accent-500)',
          }}
          animate={{ scale: [1, 0.5, 1], opacity: [1, 0.3, 1] }}
          transition={{ duration: 1, repeat: Infinity, delay: i * 0.2 }}
        />
      ))}
    </div>
  )
}
