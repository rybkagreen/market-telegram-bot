# Final Mutation Audit — 2026-04-27 — Pre-§2.B.2b verification

**HEAD:** daf5146 on feature/placement-transition-callers.

## Direct status writes — grep raw output

```
src/core/services/placement_transition_service.py:179:        placement.status = to_status
src/core/services/placement_request_service.py:761:        INV-1: placement.status='escrow' ⇒ escrow_transaction_id IS NOT NULL
src/tasks/dispute_tasks.py:108:                placement.status = new_status
src/tasks/placement_tasks.py:672:        placement.status = PlacementStatus.escrow
src/api/routers/disputes.py:704:    placement.status = new_status
src/bot/handlers/admin/disputes.py:252:    req.status = new_status
```

## setattr-style writes — empty
## .values(status=...) bulk writes — empty
## ORM dict-style writes — empty

## Hit classification

| File:line | Status | Plan ref |
|---|---|---|
| `placement_transition_service.py:179` | LEGAL — internal `_apply` | — |
| `placement_request_service.py:761` | FALSE POSITIVE — line is inside docstring (INV-1 comment) | — |
| `dispute_tasks.py:108` | DEFERRED — Шаг 3 deletes the entire file | Plan said L1158 (stale line) |
| `placement_tasks.py:672` | DEFERRED — Шаг 4 deletes `retry_failed_publication` | Plan said L638 (stale line) |
| `disputes.py:704` | DEFERRED — Шаг 1 wires through admin_override | Plan said L718 (stale line) |
| `admin/disputes.py:252` | DEFERRED — Шаг 2 rewrites handler to API call | Plan said L1011 (stale line — actual file is shorter) |

## Verdict: CLEAN

All non-legitimate hits are accounted for in §2.B.2b plan. Line numbers
in the prompt are stale (pre-§2.B.2a numbering) but file references and
semantic targets match. No surprise mutation sites discovered.
