# CHANGES — Fix plan stages for web_portal ↔ backend audit (2026-04-19)

## Scope
Подготовлен пошаговый план устранения всех проблем, найденных в
`reports/20260419_diagnostics/web_portal_vs_backend_deep.md`. План разбит
на 6 этапов, каждый — отдельный markdown-файл с конкретными задачами,
файлами, критериями завершения и порядком работы.

## Files affected
- `reports/20260419_diagnostics/FIX_PLAN_00_index.md` (new)
- `reports/20260419_diagnostics/FIX_PLAN_01_phantom_calls.md` (new)
- `reports/20260419_diagnostics/FIX_PLAN_02_contract_drift.md` (new)
- `reports/20260419_diagnostics/FIX_PLAN_03_missing_integration.md` (new)
- `reports/20260419_diagnostics/FIX_PLAN_04_backend_cleanup.md` (new)
- `reports/20260419_diagnostics/FIX_PLAN_05_arch_debt.md` (new)
- `reports/20260419_diagnostics/FIX_PLAN_06_tests_and_guards.md` (new)

## Business logic impact
None — это планирование, код не менялся.

## New / changed contracts
None.

## Overview of stages

| Этап | Приоритет | Оценка | Feature branch |
|------|-----------|--------|---------------|
| 1. Phantom calls | P0 | 6–8 ч | `fix/s-42-phantom-calls` |
| 2. Contract drift | P0 | 8–10 ч | `fix/s-43-contract-alignment` |
| 3. Missing integration | P1 | 10–14 ч | `feat/s-44-missing-integration` |
| 4. Backend cleanup | P1 | 4–6 ч | `chore/s-45-backend-cleanup` |
| 5. Arch debt | P2 | 12–16 ч | `refactor/s-46-api-module-consolidation` |
| 6. Tests + guards | P2 | 6–8 ч | `test/s-47-contract-guards` |

**Итого:** 46–62 часа.

🔍 Verified against: add7b6d (feature/s-38-escrow-recovery)
📅 Updated: 2026-04-19T12:30:00Z
