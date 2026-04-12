# Phase 8: Campaign Wizard

**Дата:** 2026-03-16
**Статус:** ✅

## Что сделано
- [x] CampaignCategory.tsx: CategoryGrid (11 категорий), reset() при mount
- [x] CampaignChannels.tsx: ChannelCard список, toggle выбор, sticky bottom панель с итого
- [x] CampaignFormat.tsx: FormatSelector (5 форматов), canUsePlan проверка, пересчёт цен
- [x] CampaignText.tsx: AI tab (3 mock варианта) + Manual tab (textarea с счётчиком)
- [x] CampaignArbitration.tsx: ArbitrationPanel для каждого канала, inline inputs, FeeBreakdown итого
- [x] CampaignWaiting.tsx: Timeline (5 шагов), детали заявки, кнопка отмены
- [x] CampaignPayment.tsx: FeeBreakdown, кнопка оплаты, предупреждение о 50% возврате
- [x] CampaignPublished.tsx: результат, распределение 85/15%, кнопка спора (48ч окно)

## CSS Modules (8 файлов)
- CampaignCategory.module.css
- CampaignChannels.module.css
- CampaignFormat.module.css
- CampaignText.module.css
- CampaignArbitration.module.css
- CampaignWaiting.module.css
- CampaignPayment.module.css
- CampaignPublished.module.css

## Проверки
- [x] `npm run build` без ошибок — 605 modules transformed
- [x] `npx tsc --noEmit` — 0 ошибок (включён в build)
- [x] Wizard flow: category → channels → format → text → terms → /247/waiting
- [x] campaignWizardStore сохраняет state между шагами (Zustand)
- [x] reset() при входе на CampaignCategory (useEffect mount)
- [x] CampaignChannels: toggle добавляет/убирает канал, sticky panel обновляет итого
- [x] CampaignFormat: недоступные форматы помечены 🔒, цена = base × multiplier
- [x] CampaignText: счётчик символов, disabled кнопка при < 10 символов
- [x] CampaignArbitration: inline inputs цены и времени, FeeBreakdown с getTotalPrice()
- [x] CampaignWaiting: Timeline 5 шагов (success/warning/default variants)
- [x] CampaignPayment: FeeBreakdown + warning 50% возврат
- [x] CampaignPublished: 85/15% split, кнопка спора условная (48ч окно)

## Технические решения
- **CategoryGrid** ожидает `{ id, label, icon }[]` — mapped из `CATEGORIES` (`key → id`, `name → label`, `emoji → icon`)
- **FormatSelector** ожидает `{ id, label, description, icon, price }[]` — mapped из `PUBLICATION_FORMATS`
- **ChannelCard** не имеет `selected` prop — выбор показан через `StatusPill` ниже карточки
- **ArbitrationPanel** не имеет rows prop — использует `children` для кастомных строк
- **Timeline** `variant` = success/warning/default (не done/active/pending)
- `navigate(-1)` нельзя типизировать напрямую — использован `navigate(-1 as unknown as string)` для navigate back
- Store не имеет `setStep()` — используется `nextStep()` при навигации вперёд

## Следующая фаза
Phase 9: Owner экраны (меню, каналы, настройки, добавление)
