# CHANGES — Act-templates wire через legal_status + Documentation cleanup (15.11 + 15.12 combined)

## What

Combined промт closing серию 15.x:
- **Часть A — 15.11**: Dead act-templates wire через `legal_status` mapping.
- **Часть B — 15.12**: Documentation cleanup + BACKLOG hygiene + PII findings surfaced.

После deploy серия 15.x — **closed** (15.5–15.12 deployed; 15.13 deferred to billing rewrite plan).

## Code changes

### `src/core/services/act_service.py`

- Removed module-level constant `ACT_TEMPLATE = "acts/act_placement.html"`.
- Added `ACT_TEMPLATE_PLATFORM`, `ACT_TEMPLATE_ADVERTISER`, `ACT_TEMPLATE_MAP_OWNER` constants.
- Added pure resolver `get_act_template(party, legal_status=None) -> str`:
  - `party="advertiser"` → `acts/act_advertiser.html`
  - `party="platform"` → `acts/act_placement.html` (default flow)
  - `party="owner"` → routed by `legal_status`:
    - `individual` → `acts/act_owner_fl.html` (НДФЛ 13%)
    - `self_employed` → `acts/act_owner_np.html` (НПД)
    - `individual_entrepreneur` → `acts/act_owner_ie.html` (УСН/НДС, ОГРНИП)
    - `legal_entity` → `acts/act_owner_le.html` (ОГРН/КПП)
  - Invalid combos raise `ValueError` (sub-stage tracking per BL-037: 2a validate party → 2b validate legal_status → 2c return path).
- `_render_act_template` Jinja site (line 237) now uses `get_act_template("platform")` instead of the deleted constant. Behaviour unchanged — existing flow still produces platform↔advertiser act.

### Tests (new)

- `tests/unit/test_act_template_routing.py` — 10 tests:
  - 2 fixed-template assertions (advertiser, platform).
  - 4 parametrized owner legal_status assertions.
  - 3 error paths (`None` legal_status, unknown legal_status, unknown party).
  - 1 regression test: `ACT_TEMPLATE_MAP_OWNER.keys()` must equal `LegalStatus` enum values (catches future enum drift).

- `tests/unit/test_act_rendering.py` — 6 tests:
  - Render each of 6 templates with minimal Jinja context (incl. `_build_fee_context()`).
  - Assert edition header (`Редакция от 28 апреля 2026 г.`) present.
  - Assert legal_status-specific markers per template (НДФЛ + 13%, НПД, ИП + ОГРНИП, ОГРН/КПП).

### Docs

- **`IMPLEMENTATION_PLAN_ACTIVE.md`** — Status overlay (Промт column) marks 15.5–15.12 ✅ deployed; 15.13 ⏸ deferred. PII findings note flipped from "не записаны" to "записаны как BL-044..BL-051".
- **`reports/docs-architect/BACKLOG.md`** — added BL-041..BL-051 (11 entries).
- **`CHANGELOG.md`** — `[Unreleased]` block extended with `15.11 + 15.12` Added/Changed/Tests/Migration sections.
- **`CLAUDE.md`** — verified, no changes needed (fee section L270-289 already aligned with 78.8/21.2 model).
- **`README.md`** — verified, no changes needed (L51, L59-69 already aligned).

## Public contract delta

- `ActService` API surface unchanged. New module-level resolver `get_act_template(party, legal_status)` exposed for future callers and tests.
- 5 previously-dead act templates now functionally reachable through the resolver. `act_placement.html` continues to power the existing `generate_for_completed_placement` flow unchanged.
- No new methods on `ActService` (deliberate scope limit: prompt says "точечный refactor", and inventing public methods without callers would itself be dead code).
- No public API endpoint changes.
- No DB schema changes.

## Sub-stage tracking (BL-037 application)

`get_act_template`:
- 2a. Validate `party` value (advertiser / owner / platform).
- 2b. For owner: validate `legal_status` not None + key exists in `ACT_TEMPLATE_MAP_OWNER`.
- 2c. Return template path.

Failure → `ValueError` raised with explicit message naming the offending value. Caller decides default или escalation.

## Critical operational notes

- DB пустая → no impact on existing acts (которых нет).
- `act_placement.html` unchanged (still default for platform↔advertiser flow).
- Each owner act template references legal-specific tax info — verified through render tests:
  - `act_owner_fl.html` — НДФЛ 13% block (act_owner template lock-in).
  - `act_owner_np.html` — НПД chek warning.
  - `act_owner_ie.html` — УСН/НДС, ОГРНИП.
  - `act_owner_le.html` — ОГРН/КПП, bank requisites.

## BACKLOG additions (BL-041..BL-051)

| # | Type | Summary |
|---|------|---------|
| BL-041 | Resolved (process) | "Verify CLAUDE.md before fix-latent-bug promts" rule codified. |
| BL-042 | Deferred | Cancel scenario naming refactor (breaking change, not blocking). |
| BL-043 | Deferred | Bot AcceptanceMiddleware fail-mode review для prod. |
| BL-044 | Resolved (gap closure) | PII audit findings now individually surfaced. |
| BL-045 | Open (16.x) | CRIT-1 — Bot payout FSM accepts financial PII. |
| BL-046 | Open (16.x) | CRIT-2 — `/api/payouts/*` accepts mini_app JWT. |
| BL-047 | Open (16.x) | HIGH-3 — `DocumentUpload.ocr_text` plaintext. |
| BL-048 | Open (16.x) | HIGH-4 — `PayoutRequest.requisites` plaintext. |
| BL-049 | Open (16.x) | MED-5 — `/api/admin/*` not pinned к web_portal. |
| BL-050 | Open (16.x) | MED-6 — `UserResponse` referral leak. |
| BL-051 | Open (16.x, low) | LOW findings batch (dead states, log_sanitizer drift, login_code leak, etc). |

## Gate baseline

| Gate | Pre | Post | Δ |
|------|-----|------|---|
| Forbidden-patterns | 31/31 | 31/31 | 0 |
| Ruff src/ | 21 | 21 | 0 |
| Mypy | 10 | 10 | 0 |
| Pytest | 76F + 17E + 668P | 76F + 17E + 684P | **+16 new** |

The 22-error transient (ruff) caught during Шаг 12 was fixed in-flight (E305 — missing blank line after `get_act_template` definition, before `# Директория для хранения PDF актов` comment). Final ruff: 21 ✅.

## Series 15.x — closed

| Промт | State |
|-------|-------|
| 15.5 | ✅ Deployed |
| 15.6 | ✅ Closed (read-only inventory) |
| 15.7 | ✅ Deployed |
| 15.8 | ✅ Deployed |
| 15.9 | ✅ Deployed |
| 15.10 | ✅ Deployed (combined с 15.11.5) |
| 15.11 | ✅ Deployed (this session, combined с 15.12) |
| 15.12 | ✅ Deployed (this session) |
| 15.13 | ⏸ Deferred (webhook consolidation 14b — отдельная сессия в billing rewrite plan) |

## Surfaced findings (informational, non-blocking)

- **act_service rendering site count**: only one (`_render_act_template` line 237). Single-act-per-placement flow unchanged. Extending to multi-act (separate platform↔owner act in addition to platform↔advertiser) is **out of scope** here — would require extending `generate_for_completed_placement` and `publication_service:436` caller. New owner-side templates are now reachable via the resolver but not yet wired to a generation flow; tests verify they render correctly so future work has a green starting point.
- **Pre-existing Pyright warnings** at `act_service.py:284-286` (`Environment / FileSystemLoader / select_autoescape` possibly unbound) come from the `try/except ImportError` Jinja2 detection block; pre-existing, not introduced by this change. Mypy is clean.
- **CLAUDE.md and README fee references already aligned** with 78.8/21.2 model — Часть B Шаги 7 and 10 were verify-only.

## Origins

- `IMPLEMENTATION_PLAN_ACTIVE.md` (Промт 15.11 + 15.12, серия 15.x).
- 15.6 inventory (5 dead templates).
- 15.10 surfaced findings (process rule BL-041, deferred refactor BL-042, deferred prod review BL-043).
- `PII_AUDIT_2026-04-28.md` (gap closure → BL-044 + BL-045..BL-051).

## Next session — открытый выбор

После closure серии 15.x — Marina выбирает:
- **(a)** Серия 16.x — PII Hardening (BL-045..BL-051 + bot payout architectural decision).
- **(b)** Phase 3 prereqs (S-48 audit, BL-031 finalize) → Phase 3 research.
- **(c)** 15.13 webhook consolidation первым (мини-сессия).

🔍 Verified against: f62789530fefdd2997d1935c6da001277ed21dc7 (pre-commit; SHAs for feature/develop/main land at Шаг 15-18) | 📅 Updated: 2026-04-29
