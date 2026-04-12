# Phase 11: API интеграция

**Дата:** 2026-03-16
**Статус:** ✅ Завершено

## Что сделано

### hooks/queries/ — 9 файлов с TanStack Query хуками
- [x] `useUserQueries.ts` — `useMe`, `useMyStats`
- [x] `usePlacementQueries.ts` — `useMyPlacements`, `usePlacement`, `useCreatePlacement` (invalidates, toast), `useUpdatePlacement` (optimistic update + rollback)
- [x] `useChannelQueries.ts` — `useMyChannels`, `useAvailableChannels`, `useChannelSettings`, `useAddChannel`, `useCheckChannel`, `useUpdateChannelSettings`, `useDeleteChannel`
- [x] `useBillingQueries.ts` — `usePlans`, `useCreateTopUp`, `useTopUpStatus` (refetchInterval 3s)
- [x] `usePayoutQueries.ts` — `usePayouts`, `useCreatePayout` (invalidates payouts + user)
- [x] `useAnalyticsQueries.ts` — `useAdvertiserAnalytics` (key: `['analytics','advertiser']`), `useOwnerAnalytics` (key: `['analytics','owner']`) — RT-001 соблюдён
- [x] `useCategoryQueries.ts` — `useCategories` (staleTime 1hr)
- [x] `useDisputeQueries.ts` — `useMyDisputes`, `useDispute`, `useCreateDispute` (optimistic), `useReplyToDispute`
- [x] `useAiQueries.ts` — `useGenerateAdText` (useMutation)
- [x] `index.ts` — barrel export

### Обновлённые экраны (31 из 31)

**Common (7/7):**
- [x] MainMenu — `useMe()` для приветствия
- [x] RoleSelect — `useMe()` для роли и тарифа
- [x] Cabinet — `useMe()` + `useMyStats()`, Skeleton loading, error state
- [x] TopUpConfirm — `useCreateTopUp()`, openLink через Telegram.WebApp
- [x] Plans — `useMe()` для текущего тарифа, fallback на константы
- [x] Help — статический, без изменений
- [x] AdvMenu — `useMe()` для тарифа в subtitle

**Advertiser (3/3):**
- [x] AdvAnalytics — `useAdvertiserAnalytics()`, Skeleton + error + retry
- [x] MyCampaigns — `useMyPlacements()`, pull-to-refresh кнопка, Skeleton
- [x] AdvMenu — `useMe()`

**Campaign Wizard (8/8):**
- [x] CampaignCategory — `useCategories()` + fallback на CATEGORIES, Skeleton
- [x] CampaignChannels — `useAvailableChannels(category)`, Skeleton, EmptyState
- [x] CampaignFormat — `useMe()` для проверки плана
- [x] CampaignText — `useGenerateAdText()` mutation, `useMe()` для лимита, Skeleton при генерации
- [x] CampaignArbitration — `useCreatePlacement()` для каждого выбранного канала, navigate к первому ID
- [x] CampaignWaiting — `usePlacement(id)`, refetchInterval 10s, auto-redirect при смене статуса
- [x] CampaignPayment — `usePlacement(id)` + `useUpdatePlacement(action:'accept')` для оплаты
- [x] CampaignPublished — `usePlacement(id)`, реальные данные 85/15% split

**Owner (10/10):**
- [x] OwnMenu — `useMe()` + `useMyPlacements({status:'pending_owner'})` для badge
- [x] OwnAnalytics — `useOwnerAnalytics()`, Skeleton, error state
- [x] OwnChannels — `useMyChannels()`, Skeleton, error, refetch кнопка
- [x] OwnAddChannel — `useCheckChannel()` + `useAddChannel()`, loading states
- [x] OwnChannelDetail — `useMyChannels()` + `useChannelSettings()`, Skeleton
- [x] OwnChannelSettings — `useChannelSettings()` + `useUpdateChannelSettings()`, Skeleton
- [x] OwnRequests — `useMyPlacements()`, Skeleton, refetch
- [x] OwnRequestDetail — `usePlacement(id)` + `useUpdatePlacement()` для accept/counter/reject
- [x] OwnPayouts — `useMe()` + `usePayouts()`, Skeleton, refetch
- [x] OwnPayoutRequest — `useMe()` + `useCreatePayout()`

**Disputes (3/3):**
- [x] OpenDispute — `usePlacement(id)` + `useCreateDispute()`, navigate к созданному диспуту
- [x] DisputeDetail — `useDispute(id)`, Skeleton, реальные данные из placement
- [x] DisputeResponse — `useDispute(id)` + `useReplyToDispute()`, Skeleton

## Проверки

- [x] `npm run build` без ошибок ✅
- [x] `npx tsc --noEmit` — 0 ошибок ✅
- [x] Все query хуки типизированы
- [x] Stale times настроены: categories 1hr, user 5min, placements 30s, channels 2min, analytics 5min, payouts 1min
- [x] Mutation хуки инвалидируют связанные queries
- [x] Mutation хуки имеют onError с toast
- [x] Skeleton loading на экранах: Cabinet, AdvAnalytics, MyCampaigns, OwnAnalytics, OwnChannels, OwnRequests, OwnPayouts, все detail экраны
- [x] Optimistic update для useUpdatePlacement (accept/counter/reject)
- [x] mockData.ts НЕ удалён (используется как fallback)
- [x] RT-001: useAdvertiserAnalytics и useOwnerAnalytics — РАЗНЫЕ queryKey

## Исправленные дефекты

- `Notification type="error"` → `type="danger"` (компонент не поддерживал "error")
- `window.Telegram.WebApp.openLink` — добавлен в `telegram.d.ts`
- Неиспользуемая переменная `category` в CampaignText удалена

## Статистика

- Query hook файлов: 9 (+ index.ts)
- useQuery хуков: 16
- useMutation хуков: 10
- Экранов обновлённых: 31 из 31

## Следующая фаза

Phase 12: Docker + Nginx + деплой
