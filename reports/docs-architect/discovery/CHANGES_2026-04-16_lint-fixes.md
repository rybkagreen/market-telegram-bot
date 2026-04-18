# Changes: lint-fixes
**Date:** 2026-04-16T16:40:32.864Z
**Author:** Claude Code
**Sprint/Task:** production-ready lint fixes

## Affected Files
- `src/api/routers/document_validation.py` — Refactored nested if to single if with and-condition for passport_page_group validation (ruff SIM102)
- `src/api/routers/document_validation.py` — Replaced equality comparison to True with direct truth check for is_readable (ruff E712, unsafe fix)
- `src/bot/handlers/owner/channel_owner.py` — Replaced if-else block with ternary operator for body assignment (ruff SIM108, unsafe fix)

## Business Logic Impact
Minor: Slight change in logic evaluation order, but no functional change intended. Unsafe fixes may affect edge cases if previous logic relied on exact True/False checks.

## API / FSM / DB Contracts
none

## Migration Notes
none

---
🔍 Verified against: <pending-commit-hash> | 📅 Updated: 2026-04-16T16:40:32.864Z