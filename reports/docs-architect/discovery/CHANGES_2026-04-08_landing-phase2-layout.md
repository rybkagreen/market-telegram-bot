# Changes: Landing Phase 2 — Layout & Core Components
**Date:** 2026-04-08T00:00:00Z
**Author:** Claude Code
**Sprint/Task:** Landing Phase 2 — Layout & Core

## Affected Files
- `landing/src/hooks/useScrollSpy.ts` — новый: активная секция по скроллу (scroll offset 80px)
- `landing/src/hooks/useConsent.ts` — новый: управление cookie-согласием (152-ФЗ), ключ `rh_cookie_consent`
- `landing/src/components/Header.tsx` — полная реализация: sticky backdrop-blur, ScrollSpy nav pills, mobile hamburger drawer (motion/react AnimatePresence)
- `landing/src/components/Hero.tsx` — полная реализация: H1 clamp(2.5rem,6vw,5rem) Outfit, motion stagger анимация, 3 stats-плитки, prefers-reduced-motion поддержка
- `landing/src/components/Footer.tsx` — полная реализация: 4-column тёмный фон #181e25, реквизиты ООО «АЛГОРИТМИК АРТС», ссылки /privacy
- `landing/src/components/CookieBanner.tsx` — новый: 152-ФЗ consent banner, fixed bottom-right, localStorage persistence, AnimatePresence exit
- `landing/src/App.tsx` — обновлён: добавлен импорт и рендер CookieBanner

## Business Logic Impact
- `useConsent` хранит согласие в localStorage (ключ: `rh_cookie_consent`), состояния: `pending | accepted | declined`
- `useScrollSpy` использует scroll event с passive listener; итерирует секции снизу вверх для определения активной
- Реквизиты ООО «АЛГОРИТМИК АРТС» отображаются в Footer (требование 152-ФЗ)
- Ссылка `/privacy` присутствует в Footer (два места) и CookieBanner
- Header компенсирует высоту через `h-16` (64px); Hero имеет `pt-16` для избежания перекрытия

## API / FSM / DB Contracts
Нет — лендинг полностью статический, нет вызовов к /api/* эндпоинтам.

## Migration Notes
Нет.

---
🔍 Verified against: cf0e7de | 📅 Updated: 2026-04-08T00:00:00Z
