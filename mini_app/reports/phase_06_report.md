# Phase 6: Общие экраны

**Дата:** 2026-03-16
**Статус:** ✅

## Что сделано
- [x] lib/mockData.ts: MOCK_USER + MOCK_REPUTATION
- [x] MainMenu.tsx: приветствие + 4 MenuButton со stagger
- [x] RoleSelect.tsx: 2 роли + текущий статус
- [x] Cabinet.tsx: балансы + тариф + репутация + налоговая инфо
- [x] TopUp.tsx: AmountChips + input + валидация
- [x] TopUpConfirm.tsx: FeeBreakdown (3.5% ЮKassa) + кнопки
- [x] Help.tsx: FAQ секции + кнопка поддержки
- [x] Plans.tsx: 4 тарифные карточки + featured Pro

## CSS Modules
- MainMenu.module.css
- RoleSelect.module.css
- Cabinet.module.css
- TopUp.module.css
- TopUpConfirm.module.css
- Help.module.css
- Plans.module.css

## Проверки
- [x] `npm run build` без ошибок — 0 errors, 593 modules transformed
- [x] `npx tsc --noEmit` — 0 ошибок (tsc -b включён в build)
- [x] MainMenu → Cabinet навигация работает (navigate('/cabinet'))
- [x] MainMenu → RoleSelect → /adv навигация работает
- [x] TopUp: выбор суммы через chips обновляет input (синхронизировано через state)
- [x] TopUp: кнопка disabled при сумме < 500 или > 300000
- [x] TopUpConfirm: calcTopUpFee — для 2000: fee=70, total=2070 (3.5% YooKassa)
- [x] Plans: текущий тариф Pro отмечен pill 'Ваш тариф'
- [x] Plans: Pro card визуально выделен (featured border + bg)
- [x] Cabinet: репутация показывает два бара (advertiser 7.4, owner 8.1)
- [x] Stagger анимации на MainMenu и Plans (motion/react)

## Технические решения
- Анимация через `motion/react` (уже в зависимостях), не framer-motion
- `StepIndicator` использует `labels[current]` — текущая метка шага
- `ReputationBar` без `variant` (компонент не поддерживает) — базовые цвета
- PLAN_INFO['business'].displayName = 'Agency 🏢' (отображается в Plans)
- TopUpConfirm: редирект на /topup если нет state.amount (через useEffect + useNavigate)

## Следующая фаза
Phase 7: Advertiser экраны (меню, аналитика, мои кампании)
