# CHANGES — Deep audit web_portal ↔ backend (2026-04-19)

## Scope
Добавлен углублённый диагностический отчёт, пересматривающий и дополняющий
предыдущую поверхностную диагностику web_portal ↔ backend.

## Files affected
- `reports/20260419_diagnostics/web_portal_vs_backend_deep.md` (new)

## Business logic impact
None — это диагностический документ, код не менялся.

## New / changed contracts (API / FSM / DB)
None.

## Summary findings (см. полный отчёт)
- **8 подтверждённых phantom-calls** (фронт дёргает несуществующие URL).
- **7 групп контрактного дрейфа** (Payout × 3 определения, User.referral_code,
  PlacementResponse.advertiser_counter_*, Contract.status, LegalProfile
  паспортные поля, Dispute дубль-тип, Channel nullable).
- **~40 orphan-эндпоинтов** на бэкенде (включая весь legacy `/api/campaigns/*`
  и половину admin-блока).
- **2 мёртвых сервиса**: `link_tracking_service.py`, `invoice_service.py`.
- **1 orphan screen**: `AdminPayouts.tsx` (файл есть, роутинг нет, бэк тоже нет).
- **22 прямых `api.*`-вызова** в обход хуков (в 10 screens + 1 component +
  1 hook).

## Action list
P0/P1/P2 разбивка приведена в разделе §7 основного отчёта.

🔍 Verified against: add7b6d (feature/s-38-escrow-recovery)
📅 Updated: 2026-04-19T12:00:00Z
