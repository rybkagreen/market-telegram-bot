# Hotfix: Tailwind v4 @source + load-fonts.js cleanup
**Date:** 2026-04-09T10:30:00Z
**Author:** Claude Code
**Type:** Hotfix

## Findings

### Tailwind v4 utility-class generation — NOT broken
Диагностика показала, что Tailwind v4 с `@tailwindcss/vite` уже сканировал
`src/**/*.tsx` автоматически через Vite-плагин. CSS 24KB — это норма для v4
(не 80-200KB как в v3): 147 уникальных utility-классов присутствуют в бандле
(flex, grid, mx-auto, items-center, justify-center, gap-*, px-*, py-* и т.д.).

Директива `@source "./**/*.{ts,tsx}"` добавлена как явное указание (страховка),
но на размер/состав CSS не повлияла — плагин уже делал это.

### load-fonts.js — удалён
`public/load-fonts.js` был артефактом предыдущей сессии — дублировал загрузку
Google Fonts через `document.createElement('link')`. Шрифты уже подключены
через `<link rel="stylesheet">` в `index.html`.

## Changes
- `landing/src/index.css`: добавлена `@source "./**/*.{ts,tsx}"` после `@import "tailwindcss"`
- `landing/index.html`: удалён `<script src="/load-fonts.js" async>` + `<noscript>` обёртка;
  добавлен прямой `<link rel="stylesheet">` на Google Fonts CSS
- `landing/public/load-fonts.js`: удалён

## Verified in production
- rekharbor.ru, portal.rekharbor.ru, app.rekharbor.ru → 200
- CSS: 147 utility-классов, gzip активен
- HTML: load-fonts.js не запрашивается
- SPA fallback /privacy → 200
- Security headers: HSTS, X-Frame-Options, CSP корректны

---
🔍 Verified against: 085d306 | 📅 Updated: 2026-04-09T10:30:00Z
