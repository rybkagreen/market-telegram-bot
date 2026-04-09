# Hotfix: Layout и стили компонентов
**Date:** 2026-04-09T14:10:00Z
**Author:** Claude Code

## Root Cause
Диагноз B/C: CSS генерировался корректно (24KB, базовые утилиты присутствовали), но
компоненты Hero, Header и Footer смешивали Tailwind utility-классы с `style={{}}` inline для
цветов, шрифтов, border-radius и теней. В результате утилитные классы цветовой палитры
(`bg-gray-100`, `text-blue-600`, `bg-gray-900`, `border-gray-200`, `shadow-sm` и т.д.)
не попадали в собранный CSS, так как в исходниках отсутствовали их строковые упоминания.

## Fix Applied
Переписаны три компонента для использования исключительно Tailwind utility-классов.
Inline `style={{}}` сохранён только там, где требуется runtime-значение (декоративный
радиальный градиент в Hero) или CSS-переменная шрифта (`var(--font-display)`).

Дополнительно: исправлена типизация вариантов анимации в Hero.tsx — добавлен импорт
`type { Variants }` из `motion/react`, `fadeUp` переименован в `itemVariants: Variants`.

## Affected Files
- `landing/src/components/Hero.tsx` — переписан: Tailwind-классы для всех цветов, теней, border-radius; анимация через `Variants` тип
- `landing/src/components/Header.tsx` — переписан: `bg-gray-100/900`, `text-gray-500/700/900`, `rounded-full`, `rounded-lg`, `border-gray-100`
- `landing/src/components/Footer.tsx` — переписан: `bg-gray-900`, `text-white/70`, `text-white/40`, `text-white/55`, `text-white/35`, `text-blue-400`, `border-white/10`

## Verified
- CSS размер после fix: 26KB (было 24KB; +2KB новые цветовые утилиты)
- `npx tsc --noEmit`: 0 ошибок
- `npm run build`: ✅ успешно
- Deploy: `docker compose build nginx && up -d --no-deps nginx` → 200 OK

---
🔍 Verified against: 085d306 | 📅 Updated: 2026-04-09T14:10:00Z
