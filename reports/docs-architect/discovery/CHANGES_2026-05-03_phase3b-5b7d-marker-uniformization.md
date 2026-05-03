# Phase 3b 5b.7d — gate marker uniformization (G07/G15/G16 PHASE4_PENDING)

**Date**: 2026-05-03
**Branch**: feature/phase3b-compliance-gates
**Commits**: 5b.7d.1 → 5b.7d.2 (1 code + 1 docs per Marina Q1=(а))
**Origin**: Phase 3b sub-block 5b.7d — final sub-block before Phase 3b closure batch. Converts G07/G15/G16 `NotImplementedError` raisers into `PHASE4_PENDING` markers (mirror G17/G18 5b.6 precedent). After 5b.7d the codebase has uniform gate-marker design — all Phase-N-pending gates return `GateResult` blockers; zero `NotImplementedError` raisers in production gate body code.

## Summary

- 5b.7d ships final Phase 3b sub-block before the closure batch: G07/G15/G16 `PHASE4_PENDING` markers + 7 docstring/comment alignments.
- Forward-looking uniformization (Marina Q4=(а)): no production callsite exercises G07 today (A.5 verified). `check_gates_for_transition` has zero production callers; `PlacementTransitionService.transition` does not consult `LegalComplianceService` (Phase 3c territory). Marker shape is ready for Phase 4 swap (marker → real body) following the established G06 разморозка precedent (5b.7a).
- Mirrors G17/G18 PHASE5_PENDING precedent from 5b.6 exactly — same body shape (`return GateResult(...)` with `passed=False`, `blocker=True`, `reason_code=GateReason.PHASE4_PENDING.value`, `remediation_url=None`), same docstring structure, same Pattern 1 (S-48) discipline, same 3-test-cases-per-gate pattern.
- 9 new unit pass tests (633 → 642). Baselines preserved (relative gate): `make ci-local` 81F/922P/6S/17E (was 81F/913P/6S/17E); ruff/mypy in-scope unchanged.

## Files modified

**Gate body files (production code):**
- `src/core/services/gates/agreement_gates.py` — full rewrite (~28 lines): G07 body returns `GateResult` marker, module docstring updated, `GateReason` import added.
- `src/core/services/gates/payout_gates.py` — G15 + G16 bodies replaced (`NotImplementedError` → `return GateResult(...)`); module docstring updated.

**Aspirational docstring/comment alignment files:**
- `src/core/enums/placement_gate.py` — module docstring (lines 9-11): "G07/G15/G16 stubs return..." → "G07/G15/G16 return reason_code='phase4_pending' (markers)..."
- `src/core/schemas/gate_result.py` — class docstring (lines 26-29): corrected `blocker=False` → `blocker=True`; added G17/G18 enumeration. Pre-5b.6-era inconsistency.
- `src/core/enums/gate_reason.py` — pre-allocation comment (lines 16-17): rewritten as concrete pattern reference.
- `src/core/services/legal_compliance_service.py` — TWO sites:
  - `_TRANSITION_GATES` preamble comment (lines 75-78): corrected wrong claim "G07/G15/G16 ARE included" — only G07 is in the table (G15/G16 are payout-side).
  - `check_gate` docstring (lines 217-218 — Q3=(а)): "all checker bodies all raise NotImplementedError" → "All checker bodies are real or Phase-N pending markers — none raise as of 5b.7d".

**Test files:**
- `tests/unit/test_agreement_gates.py` (NEW) — G07 marker test cases: `returns_phase4_marker`, `does_not_call_repos`, `marker_is_blocker` (mirror `test_payout_gates.py` G17 block).
- `tests/unit/test_payout_gates.py` — extended: import block gains `check_g15`, `check_g16`; 6 new tests appended after G18 block (3 per gate, identical pattern to G17/G18).

**Documentation:**
- `CHANGELOG.md` — Unreleased section gains 5b.7d Changed and Added subsections.
- `reports/docs-architect/discovery/CHANGES_2026-05-03_phase3b-5b7d-marker-uniformization.md` (this file, NEW).

## Commits

| # | Hash | Title |
|---|---|---|
| 5b.7d.1 | `46d4ceb` | feat(gates): G07/G15/G16 PHASE4_PENDING markers + 9 tests |
| 5b.7d.2 | (this commit) | docs(phase3b): 5b.7d closure — G07/G15/G16 marker uniformization |

## Phase A+B+C trace

Investigation file: `tmp/PHASE3B_5B7D_INVESTIGATION_2026-05-03.md` — 935 lines. Phase A enumerated current bodies (A.1), `PHASE4_PENDING` orphan status (A.2), aspirational docstring sites verbatim (A.3), `_GATE_CHECKERS` registry mapping (A.4), `_TRANSITION_GATES` exposure check incl. critical A.5 production-readiness verdict (no runtime exposure today), test surface inventory (A.6), G17/G18 mirror pattern (A.7), scope-split decision (A.8), risk assessment (A.9). Phase B specified per-site exact replacement text (B.1 G07 full file; B.2 G15+G16 + module docstring; B.3 four aspirational docstring sites; B.4 9 new unit tests verbatim; B.5 zero existing test adjustment; B.6 commit plan; B.7 Engineering Principles self-audit; B.8 Marina Q1-Q5).

8 surfaces (O.1-O.8) raised in Возражения и риски section; all resolved or deferred per Marina sign-off (see Surfaces and resolutions below).

Audit reference: `tmp/PHASE3B_PRE_CLOSURE_AUDIT_2026-05-03.md` D3.B (path correction noted per Q5).

## Marina decisions (Q1-Q5)

| # | Question | Decision |
|---|---|---|
| Q1 | Scope split: single 5b.7d (default) vs split G07 separately | **(а)** single 5b.7d, 2 commits |
| Q2 | Test count per gate | **(а)** 3 cases each, mirror G17/G18 — 9 new tests total |
| Q3 | `legal_compliance_service.py:217-218` `check_gate` docstring fix scope | **(а)** bundle into 5b.7d.1 |
| Q4 | Closure CHANGES framing for A.5 finding | **(а)** forward-looking uniformization (mention A.5 in passing — no production callsite) |
| Q5 | Audit text "src/core/results/gate_result.py" path correction | **(а)** note in closure docs (BL-015 hygiene) |

## Path correction (audit D3.B drift)

Audit referenced `src/core/results/gate_result.py:27` as the docstring location. Correct path: `src/core/schemas/gate_result.py:26-29`. There is no `src/core/results/` directory in the codebase. Investigation path-corrected; closure surfaces this drift per Q5=(а) (BL-015 cross-artifact reference accuracy preserved).

## Relationship to 5b.6 closure attribution

5b.6 closure CHANGES (`CHANGES_2026-05-03_phase3b-5b6-payout-gates.md`) established the G17/G18 PHASE5_PENDING marker pattern: `return GateResult(...)` with `blocker=True`, `passed=False`, `reason_code=GateReason.PHASE_N_PENDING.value`, `remediation_url=None`; explicit Phase boundary in body docstring; Pattern 1 (S-48) marker text as docstring footer; 3 test cases per gate (`returns_phaseN_marker`, `does_not_call_repos`, `marker_is_blocker`).

5b.7d applies this pattern identically to G07/G15/G16, substituting `PHASE4_PENDING` for `PHASE5_PENDING`. The Phase 4 swap (marker → real body via МES Acts API + КЭП verification + Мой налог real integration) follows the G06 разморозка precedent from 5b.7a (single-body change, registry untouched, marker docstring → real-now docstring, callers preserved).

After 5b.7d completion: all Phase-N-pending markers across gate-checker bodies are uniform; the codebase has zero `NotImplementedError` raisers in production gate body code. The gate-checking framework is fully equipped and uniform — ready for Phase 3c transition-time enforcement wiring + Phase 4 evaluator swaps.

## Why forward-looking, not bug-fix (A.5 rationale)

G07 IS in `_TRANSITION_GATES` for `pending_owner → pending_payment` and `counter_offer → pending_payment` transitions. However:

- `check_gates_for_transition` has **zero production callsites** outside its own definition (verified by `grep -rn "check_gates_for_transition" src/` returning only the def site).
- `PlacementTransitionService.transition` does **not** consult `LegalComplianceService` today (verified by `grep -n "compliance\|LegalCompliance\|gate\|check_gates" src/core/services/placement_transition_service.py` returning zero matches).
- Transition-time gate enforcement wiring is Phase 3c territory (separate workstream).

Therefore G07 `NotImplementedError` never raises at runtime today. Marker conversion is **uniformization** — the gate-checking framework was already fully equipped (registry + transition table + dispatcher), but only the body shape was non-uniform (3 raisers + 15 markers/real-bodies). After 5b.7d the body shape is uniform across all 18 gates. No production callsite is changed by 5b.7d.

When Phase 3c integration lands (`PlacementTransitionService.transition` invoking `LegalComplianceService.check_gates_for_transition`), G07's marker will surface as a `TransitionBlockedError` with `reason_code='phase4_pending'`, distinguishable from real-fail reasons. Phase 4 evaluator swap will then test the real condition; if it passes, the transition proceeds; if it fails, the blocker remains. The marker's interim semantics are by design.

## Marker design rationale (mirrors 5b.6 G17/G18)

- `passed=False` — gate has not affirmatively confirmed the underlying condition (Phase 4 evaluator missing).
- `blocker=True` — in any caller that interprets `blocker`, the marker prevents the transition until Phase 4. Phase 4 swap will test the real condition; if it passes, transition proceeds; if it fails, blocker remains.
- `reason_code='phase4_pending'` — distinct from any real-fail reason (e.g. `framework_contract_unsigned`, `act_not_generated`). Closure CHANGES attribution explicit; future API surface (Phase 3d `GET /api/placements/{id}/gates`) can render markers distinctly from real fails.
- `remediation_url=None` — no portal route exists until Phase 4 ships UI for Acts upload / signature / receipt issuance (mirror G17/G18).

## Verification

| Gate | Pre-5b.7d | Post-5b.7d.1 | Post-5b.7d.2 |
|---|---|---|---|
| ruff (`src/`) | 4 errors (pre-existing, unchanged scope) | 4 (no regression) | 4 |
| mypy (`src/`) | 10 errors | 10 (no regression) | 10 |
| pytest unit (excl test_main_menu) | 62F / 633P / 1E | 62F / **642P** / 1E (+9) | unchanged |
| `make ci-local` aggregate | 81F / 913P / 6S / 17E | 81F / **922P** / 6S / 17E (+9) | unchanged |
| Alembic head | `e6a88faa9fa0` | unchanged | unchanged |
| `NotImplementedError` in gate bodies | 3 (G07 / G15 / G16) | **0** | 0 |
| Smoke import G07/G15/G16 markers | n/a (raises) | All return `GateResult(reason_code='phase4_pending', blocker=True, passed=False, remediation_url=None)` | unchanged |

Note: ruff in-scope baseline measured at HEAD `9a8e9ef` was 4 errors (`src/api/routers/document_validation.py:107` SIM102; `:263` E712; `src/bot/handlers/owner/channel_owner.py:82` SIM108; `src/tasks/placement_tasks.py:380` F841). Investigation Шаг 0 cited "0 errors" but actual measurement found 4 — these are pre-existing in files not touched by 5b.7d. Verified via `git stash && ruff check src/`. L37 surprise (see Lessons).

## Surfaces and resolutions

Per investigation Возражения и риски section:

- **O.1** — A.5 finding re-frames sub-block as forward-looking, not bug-fix. **RESOLVED** via Q4=(а) closure framing.
- **O.2** — Comment drift at `legal_compliance_service.py:75-78` (claimed "G07/G15/G16 ARE included" but only G07 is). **RESOLVED** via B.3 site 4 fix.
- **O.3** — Aspirational docstring at `gate_result.py:26-29` is internally inconsistent (described `blocker=False` for marker shape that always was `blocker=True` post-5b.6). **RESOLVED** via B.3 site 2 fix (corrected to `blocker=True`).
- **O.4** — Audit D3.B path drift (`src/core/results/` → `src/core/schemas/`). **RESOLVED** via Q5=(а) note in this closure (BL-015 hygiene).
- **O.5** — Out-of-scope module-docstring stale text (e.g. `legal_compliance_service.py:1-8` "Phase 3a Block 2 ships only the dispatch skeleton" — out of strict 5b.7d scope per P1). **DEFERRED** to Phase 3b closure batch (broader stale-docstring sweep).
- **O.6** — `payout_gates.py` module docstring "G15/G16 remain Phase 4 stubs". **RESOLVED** via B.2 module docstring update.
- **O.7** — `agreement_gates.py` module docstring "Phase 4 stub". **RESOLVED** via B.1 full file rewrite.
- **O.8** — Snapshot file `tests/unit/snapshots/gate_result_response.json` unaffected. **VERIFIED** (positive); enum names unchanged; only body internals change. No `UPDATE_SNAPSHOTS=1` regeneration needed.

## Deferred to production launch / Phase 3 closure batch

These items are out of strict 5b.7d scope (P1 boundary discipline) and are surfaced for the upcoming Phase 3b closure batch / production-launch gate. NOT inline BACKLOG — consolidate at closure batch.

- **Phase 4 G07 real body** — query Acts table for placement's supplementary-agreement Act, verify both signatures present (МES Acts API + КЭП verification).
- **Phase 4 G15 real body** — verify Act has both advertiser-side and owner-side signatures via КЭП (МES Acts API + КЭП crypto integration).
- **Phase 4 G16 real body** — call Мой налог real provider, verify receipt accepted with persistent receipt-id (replaces current synthetic receipt-id flow).
- **Phase 3c transition-time gate enforcement wiring** (re-surfaces from A.5) — `PlacementTransitionService.transition` should invoke `LegalComplianceService.check_gates_for_transition` before allowing transition. Today the framework is ready (registry + transition table + dispatcher + uniform body shape) but integration is not wired. **BLOCKER for production launch**: placements могут transition without gate enforcement. Phase 3c territory.
- **Broader stale module-docstring sweep** (re-surfaces from O.5) — `legal_compliance_service.py:1-8` says "Phase 3a Block 2 ships only the dispatch skeleton. Gate-checker logic lives in src/core/services/gates/ (Phase 3b stubs)." After 5b.3-5b.7d, gate-checker logic is largely real, not stubs. Phase 3b closure batch territory.
- **Aspirational docstring monitoring** — current investigation pattern (drift in both directions: stale-positive lies + stale-negative future-tense + internally-inconsistent contracts) is generalizable. Phase 3 closure batch should include a systematic sweep.
- **4 pre-existing ruff `src/` errors** (`document_validation.py:107`/`:263`, `channel_owner.py:82`, `placement_tasks.py:380`) — out of 5b.7d scope; surfaced for Phase 3b closure batch lint pass.

## Lessons (for Phase 3 closure batch — NOT inline BACKLOG)

### L37 — Measure baseline at HEAD, do not cite from prior reports

5b.7c surprise (audit-vs-pre-5b.7c kickoff baseline drift on identical HEAD `02bf454`) showed cited baselines accumulate non-deterministic test-flake drift between sessions. 5b.7d Шаг 0 explicitly measured fresh — pytest unit and `make ci-local` matched investigation pre-flight numbers exactly (62F/633P/1E and 81F/913P/6S/17E).

**Independent re-surfacing in 5b.7d:** investigation cited ruff `src/` baseline as 0 errors. Actual measurement found 4 pre-existing errors in untouched files. Verified via `git stash && ruff check src/` — they exist at HEAD `9a8e9ef` and were not introduced by 5b.7d. Investigation pre-flight section "in-scope clean" was inaccurate (likely conflated with whichever subset was measured). 5b.7d output ruff = 4 (preserved baseline).

Pattern for future sub-blocks: prompt baselines are **expected reference**; agent's first action is **measure actual**. Compare both, surface deviation; never silently use prompt numbers. Prompt numbers can be wrong even when investigation is otherwise accurate (Phase A enumerates code state, not lint output).

### L38 — Aspirational docstrings drift in BOTH directions

Stale docstrings come in two flavors and audits must surface both:

- **Stale-positive** — text says feature exists but code doesn't yet (e.g. `gate_result.py:26-29` originally described "Phase 3a stubs use reason_code='phase4_pending' for G07/G15/G16" — text claimed a contract that didn't exist; G07/G15/G16 actually raised `NotImplementedError`).
- **Stale-negative / internally-inconsistent** — text describes a contract incorrectly that it never matched (e.g. same docstring described `blocker=False` for marker shape that always was `blocker=True` post-5b.6 — the docstring was wrong about its own enum contract).

5b.7d audit O.3 caught this — the text described `blocker=False` but G17/G18 used `blocker=True`. Pre-existing inconsistency, correction bundled with body change.

Pattern: when surfacing aspirational docstrings, audit BOTH (a) does the code do what the text claims? AND (b) is the text internally consistent with the actual contract? Stale-positive often dominates audit attention; stale-negative is easier to miss but equally harmful to future maintainers.

### L39 — Gate framework readiness ≠ transition-time enforcement wiring

By 5b.6/5b.7a/5b.7b/5b.7c/5b.7d completion, the gate framework is fully equipped:

- `_TRANSITION_GATES` table populated (5b.2)
- `_GATE_CHECKERS` registry populated with real or marker bodies (5b.3-5b.7d)
- User-side dispatchers operational (5b.7a)
- `PayoutComplianceService` skeleton (5b.7b)
- `_GATE_CHECKERS` body shapes uniform — markers + real bodies, no raisers (5b.6/5b.7d)

However `PlacementTransitionService.transition` does **not** invoke `check_gates_for_transition` today — that wiring is Phase 3c territory (verified A.5: zero `compliance|gate|check_gates` matches in `placement_transition_service.py`). Framework readiness ≠ integration completion.

Phase 3 closure batch must surface this gap explicitly: it is a **BLOCKER for production launch** — placements могут transition without gate enforcement today. The framework is ready when the wiring lands; the wiring is the missing piece. Closure docs should label this explicitly under "production-launch blockers" so it's not silently inherited.

## Out of scope

- Phase 4 / Phase 5 evaluator real bodies (G07/G15/G16 real bodies require МES Acts API + КЭП + Мой налог real integration; Phase 4 territory).
- Phase 3c transition-time gate enforcement wiring (`PlacementTransitionService.transition` integration with `LegalComplianceService.check_gates_for_transition`) — separate workstream, separate sub-block.
- Frontend changes (mini_app/, web_portal/, landing/).
- Schema/migration changes (alembic head `e6a88faa9fa0` unchanged).
- Broader stale module-docstring sweep (e.g. `legal_compliance_service.py:1-8` Phase 3a-era text — O.5 deferred to Phase 3b closure batch).
- `_GATE_CHECKERS` registry changes (function symbols unchanged in 5b.7d).
- `_TRANSITION_GATES` table changes (only the surrounding comment per O.2).
- `placement_transition_service.py` (Phase 3c).
- Snapshot regeneration (verified O.8 unaffected; enum names unchanged).
- 4 pre-existing ruff errors in untouched files (`document_validation.py`, `channel_owner.py`, `placement_tasks.py`) — out of 5b.7d scope; surfaced for closure batch.

🔍 Verified against: `46d4ceb` (5b.7d.1) | 📅 2026-05-03
