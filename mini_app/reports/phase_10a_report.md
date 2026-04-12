# Phase 10a: Owner — заявки + выплаты

**Дата:** 2026-03-16
**Статус:** ✅

## Что сделано
- [x] mockData.ts: MOCK_OWNER_REQUESTS (4 заявки: 2 pending_owner, 1 published, 1 cancelled) + OwnerRequest тип
- [x] OwnRequests.tsx: 3 фильтра (новые/опубликованные/отклонённые) + RequestCard + actions под карточками
- [x] OwnRequestDetail.tsx: ArbitrationPanel + текст объявления + принять/контр-предложение/отклонить по статусу
- [x] OwnPayouts.tsx: доступный баланс (earned_rub) + история выплат из MOCK_PAYOUTS
- [x] OwnPayoutRequest.tsx: AmountChips + «Всё» кнопка + FeeBreakdown (1.5%) + реквизиты + валидация

## Проверки
- [x] `npm run build` — ✓ built in 315ms
- [x] `npx tsc --noEmit` — 0 ошибок
- [x] OwnRequests: 3 фильтра, counts: new=2, published=1, cancelled=1 ✅
- [x] OwnRequestDetail: ArbitrationPanel показывает рекламодателя, формат, цену, скидку, время ✅
- [x] OwnRequestDetail: отклонение disabled при комментарии < 10 символов ✅
- [x] OwnRequestDetail: контр-предложение с inputs цены и времени (доступно когда count < 3) ✅
- [x] OwnPayouts: показывает earned_rub + 2 выплаты из истории ✅
- [x] OwnPayoutRequest: calcWithdrawalFee правильный (5000 → fee 75 → net 4925) ✅
- [x] OwnPayoutRequest: кнопка disabled при amount < 1000 или details < 5 символов ✅

## Проблемы
`failed_permissions` не входит в тип `RequestStatus` компонента RequestCard — решено маппингом в `failed` через функцию `toCardStatus`.

## Следующая фаза
Phase 10b: Диспуты (3 экрана)
