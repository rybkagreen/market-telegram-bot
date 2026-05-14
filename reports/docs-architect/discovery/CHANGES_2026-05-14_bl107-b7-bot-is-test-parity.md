# CHANGES 2026-05-14 — BL-107 Phase B.7 (O.7 carve-out closure — bot is_test parity)

## Context

Closes the **O.7 5b.7a deferred carve-out** identified during Phase 4 channel-add
hookup work. The bot path `add_channel_confirm` previously hardcoded
`is_test=False` because there was no FSM step to capture the admin's choice,
while the API path (`POST /api/channels`) already supported `body.is_test +
is_admin` gate (Phase B.4 wiring). Phase B.7 closes that asymmetry: admins now
get a dedicated FSM step (`selecting_is_test`) с inline keyboard choice
between Тестовый / Реальный канал.

Non-admin UX is preserved exactly — they skip the new step и proceed directly
to confirmation with `is_test=False` default.

**Scope envelope:** narrow surgical change — single bot handler file + FSM
states module + new test file. No frontend, no API, no schema/migration, no
service-layer changes.

Built atop Phase B.6 (`5485729`).

## Changes

### Modified — `src/bot/states/channel_owner.py`

Added one state to `AddChannelStates` enum:

```python
class AddChannelStates(StatesGroup):
    entering_username = State()
    selecting_category = State()
    selecting_is_test = State()  # NEW — admin-only branch
    confirming = State()
```

Order matters только при reading — runtime semantics determined by handler
routing. Placed between `selecting_category` и `confirming` to reflect the
flow.

### Modified — `src/bot/handlers/owner/channel_owner.py`

**Imports (+2):**

- `InlineKeyboardMarkup` (для `_build_is_test_keyboard()` return type)
- `Category` (для `_render_add_channel_confirmation()` parameter type)

**New module-level helpers (2):**

- `_build_is_test_keyboard() -> InlineKeyboardMarkup` — inline keyboard
  с buttons "Реальный канал" / "Тестовый канал" / Cancel.
  Callback data: `own:add_channel:is_test:0` / `:1` / `main:my_channels`.
- `async _render_add_channel_confirmation(callback, data, category)` —
  extracted confirmation UI rendering из `add_channel_select_category`.
  Caller has already set state=confirming + populated FSM data. Helper
  reads `data.get("is_test", False)` и adds 🧪 *Тестовый канал* (admin)
  line in summary if True.

**Handlers (3 modified, 1 new):**

1. **`add_channel_select_category` — branching.** After capturing category
   slug, looks up user. If `user.is_admin` → sets state to
   `selecting_is_test`, shows is_test keyboard. Else → sets `is_test=False`
   в FSM data, sets state to `confirming`, calls
   `_render_add_channel_confirmation`. Preserves existing non-admin UX.

2. **NEW — `add_channel_select_is_test`.** Matched by
   `F.data.startswith("own:add_channel:is_test:")` + `AddChannelStates.
   selecting_is_test`. Capture: `is_test = raw == "1"`. Defense-in-depth
   `user.is_admin` check (rejects with alert + state.clear() if somehow
   reached by non-admin). Updates FSM data, sets state=confirming, looks
   up category by slug from data, renders confirmation.

3. **`add_channel_confirm` — read is_test from FSM.**
   - Replaced `is_test=False,  # O.7 deferred to Phase B.7` с
     `is_test=is_test_flag` где `is_test_flag = bool(data.get("is_test",
     False))`.
   - Added defense-in-depth guard immediately after user lookup: if
     `is_test_flag and not user.is_admin` → reject with alert + state.clear()
     + return. Belt-and-suspenders для stale state или direct callback
     injection scenarios.
   - TelegramChat construction теперь passes `is_test=is_test_flag` (was
     relying on column default False — explicit now).

### New file — `tests/unit/test_bl107_bot_is_test_flow.py`

8 pure unit scenarios, AsyncMock-only:

| # | Scenario | Verifies |
|---|---|---|
| 1 | Admin user reaches selecting_is_test | `state.set_state(selecting_is_test)`, keyboard shown |
| 2 | Non-admin skips to confirming | `state.set_state(confirming)`, is_test=False в FSM data |
| 3 | Admin chooses is_test:1 | `update_data(is_test=True)`, state=confirming |
| 4 | Admin chooses is_test:0 | `update_data(is_test=False)`, state=confirming |
| 5 | Defense-in-depth non-admin at is_test handler | `callback.answer(show_alert=True)`, `state.clear()`, no FSM update |
| 6 | add_channel_confirm — admin is_test=True flow | TelegramChat created с is_test=True |
| 7 | add_channel_confirm defense-in-depth — non-admin + is_test=True | rejected, state cleared, no session.add |
| 8 | add_channel_confirm — non-admin default | TelegramChat created с is_test=False |

Reuses test fixtures pattern из existing `test_bot_channel_owner.py`:
autouse `isinstance` bypass, MagicMock-based callback/state/session.

### Modified — `CHANGELOG.md`

Added Phase B.7 entry под `[Unreleased]`. Documents added items, behavior
change, и closure of O.7 deferred carve-out.

## Verification

- `make typecheck`: 0/305 ✓
- `make lint`: 7 baseline preserved (all 7 in `tests/unit/conftest.py` — BL-024) ✓
- `make format`: clean (applied на этой PR) ✓
- `alembic check`: drift-free ✓ (Phase B.7 не touches schema)
- `pytest tests/unit/test_bl107_bot_is_test_flow.py`: 8/8 ✓
- `pytest tests/unit/test_bot_channel_owner.py`: 4/4 ✓ (existing happy/decline paths preserved)
- `pytest tests/unit/test_bl107_*.py`: 97/97 ✓ (89 prior + 8 new)

## Untouched (per Phase B.7 scope envelope)

- **API endpoints** — Phase B.5a stable; bot path теперь mirrors API gate
- **Frontend (web_portal/mini_app)** — Phase B.5b stable
- **Schema / migrations** — Phase B.1 done; no model changes
- **Gate framework** — Phase B.2 stable
- **Telegram helpers** — Phase B.3 stable (only consumed)
- **Channel-add hookup core** — Phase B.4 stable (Trustchannelbot verify call site unchanged)
- **Admin review** — Phase B.5a/b stable
- **Periodic re-verification task** — Phase B.6 stable
- **BL-002 mock infrastructure** — Phase B.8 (Phase B.7 tests mock everything в-pure-Python)
- **E2E / Playwright** — Phase B.9
- **BACKLOG.md** — deferred к BL-107 closure

## Decisions echoed (no new architectural moves — just closing O.7)

- **FSM state location:** New state `selecting_is_test` placed между
  `selecting_category` и `confirming` reflecting логического flow order.
- **Callback data scheme:** `own:add_channel:is_test:0` / `:1` follows
  existing `own:add_channel:*` prefix convention. Single handler с
  startswith match + last-segment parse (matches `own:add_channel:cat:*`
  handler pattern).
- **Defense-in-depth: 2 admin checks.** First at FSM gate
  (`selecting_is_test` handler) — primary. Second в `add_channel_confirm`
  — covers stale state / direct callback injection. Trades 1 extra DB
  lookup for robustness; acceptable since this code path is rare и
  security-relevant.
- **TelegramChat is_test passed explicitly.** Was relying on column default
  False; теперь passes `is_test=is_test_flag` для clarity. Behavior
  identical for is_test=False but explicit makes intent obvious.
- **No back button on is_test keyboard.** Only Cancel. Matching prompt spec
  и keeping FSM transition graph simple. Admin who wants to change
  category just cancels и restarts.
- **Confirmation UI shows is_test marker.** Если admin chose Тестовый, the
  confirmation summary adds 🧪 *Тестовый канал* (admin) line — gives admin
  visual confirmation perед finalizing.

## What BL-107 Phase B.7 delivers (operational)

After deploy + bot restart:

- Non-admin owner adding channel: identical UX к pre-B.7 — category →
  confirmation → submit. `is_test=False` written to DB (default).
- Admin owner adding channel: category → **NEW step: is_test choice** →
  confirmation → submit. `is_test=True/False` written to DB per choice.
- Bot/API symmetry: both paths теперь support test channel creation для
  administrators. No surprise asymmetry для admin who uses both interfaces.

Combined с phases B.1–B.6, BL-107 has full coverage:

- **Add-time enforcement** (B.4) — channel-add G19 + Trustchannelbot check
- **Manual escape hatch** (B.5a/b) — owner submission + admin review
- **Drift detection** (B.6) — daily background re-verification
- **Bot UX parity** (B.7) — admin is_test choice matches API capability

Remaining BL-107 work:

- **Phase B.8** — BL-002 mock infrastructure (aiohttp stub + docker-compose.test.yml)
- **Phase B.9** — E2E Playwright tests + component tests (vitest) for B.5b screens

🔍 Verified against: branch HEAD pre-commit | 📅 Created: 2026-05-14
