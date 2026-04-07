import * as Sentry from '@sentry/react'

if (import.meta.env.VITE_SENTRY_DSN) {
  Sentry.init({
    dsn: import.meta.env.VITE_SENTRY_DSN as string,
    environment: import.meta.env.MODE,
    tracesSampleRate: 0.05,
    sendDefaultPii: false,
    beforeSend(event) {
      if (event.request?.headers) {
        delete (event.request.headers as Record<string, string>)['Authorization']
        delete (event.request.headers as Record<string, string>)['authorization']
      }
      return event
    },
  })
}

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './styles/globals.css'

// Проверяем, есть ли сохранённый токен — если нет, редирект на /login
import('./App').then(({ default: App }) => {
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
})
