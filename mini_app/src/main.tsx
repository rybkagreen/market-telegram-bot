import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './styles/tokens.css'
import './styles/globals.css'
import './styles/animations.css'

const tg = window.Telegram?.WebApp

if (!tg || !tg.initData) {
  document.getElementById('root')!.innerHTML = `
    <div style="
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      background: #0b0e14;
      color: #e8ecf4;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      gap: 16px;
      padding: 24px;
      text-align: center;
    ">
      <div style="font-size: 64px; line-height: 1;">⚓</div>
      <h1 style="margin: 0; font-size: 24px; font-weight: 700;">RekHarborBot</h1>
      <p style="margin: 0; font-size: 16px; color: #8892a4;">
        Это приложение доступно только через Telegram
      </p>
      <a
        href="https://t.me/RekharborBot"
        style="
          margin-top: 8px;
          border: 1.5px solid #0ea5e9;
          border-radius: 12px;
          padding: 12px 24px;
          color: #0ea5e9;
          text-decoration: none;
          font-size: 15px;
          font-weight: 500;
        "
      >
        Открыть в Telegram →
      </a>
    </div>
  `
} else {
  tg.ready()
  tg.expand()
  document.documentElement.setAttribute('data-theme', tg.colorScheme || 'dark')

  import('./App').then(({ default: App }) => {
    createRoot(document.getElementById('root')!).render(
      <StrictMode>
        <App />
      </StrictMode>,
    )
  })
}
