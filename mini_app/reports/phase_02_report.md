# Phase 2: Design Tokens + Глобальные стили

**Дата:** 2026-03-16
**Статус:** ✅ Выполнено

## Что сделано

- [x] tokens.css: все CSS переменные (dark theme на :root)
- [x] tokens.css: [data-theme='light'] переопределения (bg, text, shadow, glass)
- [x] tokens.css: Telegram theme vars fallback (--tg-theme-bg-color, --tg-theme-text-color, --tg-theme-button-color)
- [x] globals.css: Google Fonts import (Outfit, DM Sans, JetBrains Mono) с display=swap
- [x] globals.css: CSS reset (* { box-sizing: border-box }, -webkit-tap-highlight-color, antialiasing)
- [x] globals.css: scrollbar, selection, focus-visible стилизация
- [x] globals.css: safe-area классы (.safe-area-top/bottom/x с env())
- [x] globals.css: utility классы (typography, layout, interactive)
- [x] animations.css: 9 keyframes (fadeIn, fadeInUp, fadeInDown, slideInRight, slideInLeft, scaleIn, pulse, shimmer, spin)
- [x] animations.css: utility классы (.animate-*, .skeleton, .stagger-1..6)
- [x] animations.css: prefers-reduced-motion поддержка
- [x] DesignSystemTest.tsx: визуальная проверка всех токенов (цвета, типографика, тени, glass, анимации, spacing, radii)
- [x] Переключение dark/light работает (кнопка в DesignSystemTest)
- [x] App.tsx обновлён на DesignSystemTest

## Проверки

- [x] `npm run build` без ошибок (155ms, CSS 6.99kB gzip 2.22kB)
- [x] `npx tsc --noEmit` — 0 ошибок
- [x] Шрифты: Outfit, DM Sans, JetBrains Mono через Google Fonts CDN
- [x] Тёмная тема: bg-primary #0b0e14, text #e8ecf4, accent #0ea5e9
- [x] Светлая тема: bg-primary #f8fafc, text #0f172a, accent не меняется
- [x] Skeleton shimmer анимация (1.5s ease infinite)
- [x] Glass: backdrop-blur 12px + полупрозрачный фон
- [x] Stagger анимации: 6 уровней 50ms..300ms

## Количество токенов

- CSS переменных --rh-* в tokens.css: **97**
  - Цветовых (dark + light): ~36
  - Типографических (шрифты, размеры, leading, weight): 22
  - Spacing: 11
  - Прочих (radii, shadows, glass, transitions, z-index): 28
- @keyframes в animations.css: **9**
- Utility классов (.animate-*, .skeleton, .stagger-*, .text-*, .flex-*, .stack*, .grid-*): **~28**

## Проблем не было

## Следующая фаза

Phase 3: Telegram SDK интеграция + Auth flow + TypeScript типы + API клиент
