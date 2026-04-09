# Changes: Landing Phase 3 — ESLint 9 + Content Sections
**Date:** 2026-04-09T00:00:00Z
**Author:** Claude Code
**Sprint/Task:** Landing Phase 3

## Affected Files
- `landing/eslint.config.js` — новый: ESLint 9 flat config (TS + React + jsx-a11y + globals)
- `landing/package.json` — ESLint 9 плагины добавлены в devDependencies; scripts `lint`/`lint:fix` обновлены
- `landing/index.html` — добавлен `<script data-schema="faq">` placeholder для FAQ JSON-LD
- `landing/src/App.tsx` — добавлены импорты и рендер Features, HowItWorks, Tariffs, Compliance, FAQ
- `landing/src/components/Features.tsx` — новый: 6 карточек фич (эскроу, ОРД, AI, репутация, мониторинг, торг); stagger motion/react
- `landing/src/components/HowItWorks.tsx` — новый: двухрежимный флоу с pill-переключателем (AnimatePresence); шаги advertiser (4) + owner (3)
- `landing/src/components/Tariffs.tsx` — новый: 4 карточки из constants.ts; Pro выделен border-brand-blue; динамический PLATFORM_COMMISSION
- `landing/src/components/Compliance.tsx` — новый: 4 блока (ОРД/erid, 152-ФЗ, эскроу, репутация)
- `landing/src/components/FAQ.tsx` — новый: аккордеон (один открытый), FAQ JSON-LD записывается в `<head>` через useEffect
- `landing/src/screens/Privacy.tsx` — полный текст 152-ФЗ: оператор ООО «АЛГОРИТМИК АРТС», цели обработки, права пользователя, cookie, передача ОРД/YooKassa

## Business Logic Impact
- Цены тарифов рендерятся из `TARIFFS` и `PLATFORM_COMMISSION` (constants.ts) — не хардкодятся
- FAQ JSON-LD (`FAQPage` schema.org) инжектируется динамически после монтирования компонента
- Все тексты основаны на реальных механиках платформы из QWEN.md (эскроу ESCROW-001, ОРД Яндекс API v7, репутация 0.0–10.0, 3 раунда торга)
- OWNER_SHARE и COMMISSION_PCT вычисляются из PLATFORM_COMMISSION динамически

## API / FSM / DB Contracts
Нет — лендинг статический, без API-вызовов.

## Migration Notes
Нет.

---
🔍 Verified against: 085d306 | 📅 Updated: 2026-04-09T00:00:00Z
