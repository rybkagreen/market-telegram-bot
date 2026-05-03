# Phase 3b Closure Batch — Final consolidation (2026-05-03)

**Phase 3b series:** complete (10 sub-blocks 5b.1-5b.7d)
**Branch:** `feature/phase3b-compliance-gates`
**HEAD pre-batch:** `402d7dc`
**HEAD post-batch (this file's commit):** `<recorded post-merge in commit log>`
**Commits ahead of develop pre-merge:** 34 (sub-blocks) + 4 (closure-batch) = 38
**Merge target:** develop → main `--no-ff` per Q1
**Tag:** `v0.3.0-phase3b` per Q2

## Phase 3b summary

10 sub-blocks shipped infrastructure для legal-compliance gate enforcement:

- **5b.1** schema additives (gate-related fields, payout_request.idempotency_key)
- **5b.2** transition→gates resolution table + dispatcher
- **5b.3** Advertiser gates G01-G03 (legal profile, framework contract, INN/OGRN/OGRNIP checksum)
- **5b.4** Owner gates G04-G06 (parallel structure)
- **5b.5** Publication gates G08-G12 (ERID, ORD report, text marking, post-publication verify)
- **5b.6** Payout gates G13/G14 real + G17/G18 PHASE5_PENDING markers
- **5b.7a** Channel-add hook (BL-037 production gap closure) + G06 разморозка + user-role gate dispatcher
- **5b.7b** PayoutComplianceService skeleton + X-Idempotency-Key keying convention + 3 P4 cleanups
- **5b.7c** S-48 hygiene sweep (43 sites, 5 commits)
- **5b.7d** Gate marker uniformization (G07/G15/G16 PHASE4_PENDING) + 7 docstring alignments

**Phase 3b net contribution:**

- +119 unit pass tests (523 → 642), 0 introduced failures, 0 introduced errors
- 18 gates total (G01-G18): G01-G14 real bodies; G07/G15-G18 PHASE-N pending markers
- 4 dispatch services: LegalCompliance (legacy + user-role), PayoutCompliance skeleton
- ruff/mypy baselines preserved exactly через 34 commits

## Phase 3b is closed

This is the FINAL sub-block of Phase 3b. After this closure batch:

- All 5b.X sub-blocks ✅ complete
- Phase 3b boundary tagged `v0.3.0-phase3b`
- Phase 3c (transition-wiring) is next phase — separate sub-block charter

## Files changed (closure batch)

| Commit | File | Type |
|---|---|---|
| 3b.closure.1 | `IMPLEMENTATION_PLAN_ACTIVE.md` | Status overlay + Branch HEADs + L22/L25 plan revision |
| 3b.closure.2 | `BACKLOG.md` | BL-072/073/074 + last-updated stamp |
| 3b.closure.3 | `CHANGES_2026-05-03_phase3b-closure-batch.md` (NEW, this file) | Master closure |
| 3b.closure.4 | `CHANGELOG.md` | `[Unreleased]` → `[v0.3.0-phase3b] - 2026-05-03` |

## Lessons L17-L39 (consolidated for posterity)

23 architectural lessons surfaced through 7 closure files (5b.1 + 5b.4 yielded none — schema additives and parallel-pattern owner gates surfaced no new lessons).

| L# | Source | One-line summary |
|---|---|---|
| L17 | 5b.2 | Agent self-audit catches planner-side prompt drift (Q4 unused `user` param) |
| L18 | 5b.3 | `Contract.contract_type` hardcoded "advertiser_framework" for both roles (rename pending → T3.20) |
| L19 | 5b.3 | `LegalProfileService.check_completeness` has side effects (writes + flush; pure-compute split deferred → T3.21) |
| L20 | 5b.5 | Skeleton `YandexOrdProvider` in `ord_yandex_provider.py` is dead code (real impl: `yandex_ord_provider.py`; removal → T3.17) |
| L21 | 5b.6 | `_TRANSITION_GATES` exclusion of G13-G18 is documented intent, not a gap (PayoutComplianceService is future invoker) |
| L22 | 5b.6 | Plan §3.B.1 phrasing "Pre-payout (completed → payout_processing)" terminology drift (RESOLVED inline в closure batch via Q9=(а)) |
| L23 | 5b.7a | G06 `PHASE5_PENDING` marker in 5b.4 was conservative over-marking (rollback acceptable when wiring requires real semantics) |
| L24 | 5b.7a | `LegalComplianceService.check_gate(gate, placement)` doesn't fit non-transition contexts (channel-add) → user-role dispatcher added |
| L25 | 5b.7a | Plan §3.B.6 admin test-mode carve-out language missing (RESOLVED inline в closure batch via Q9=(а)) |
| L26 | 5b.7b | Skeleton with populated dispatchers (Option A) over all-NotImplementedError |
| L27 | 5b.7b | Service partition via naming convention (`*_payout_*` returns ONLY payout-specific gates) |
| L28 | 5b.7b | IntegrityError strict-distinguish over broad catch |
| L29 | 5b.7b | Skeleton signature impedance — NotImplementedError as design boundary, not workaround |
| L30 | 5b.7b | `tests/integration/test_payout_concurrent.py` direct-call check (FastAPI Header dep pre-flight) |
| L31 | 5b.7b | Single source of truth for DB constraint names (module-level constant) |
| L32 | 5b.7b | Driver-API divergence helpers (asyncpg vs aiosqlite IntegrityError shapes) |
| L33 | 5b.7b | P4 once-correctly cleanups bundled threshold rule (escalated → T2.3/T2.4 via O.4) |
| L34 | 5b.7c | Audit re-classification before execution (catches mis-classification mid-audit) |
| L35 | 5b.7c | Pattern 3 markers only for legitimately-paired-with-external-side-effect callsites |
| L36 | 5b.7c | Explicit `flush()` only where downstream code reads from session |
| L37 | 5b.7d | Measure baseline at HEAD, do not cite from prior reports |
| L38 | 5b.7d | Aspirational docstrings drift in BOTH directions (positive lies + negative future-tense) |
| L39 | 5b.7d | Gate framework readiness ≠ transition-time enforcement wiring (Phase 3c work → T1.1) |

Per Q4=(б), no L17-L39 lesson is promoted to CLAUDE.md в this closure batch. All retained in this file для retrospective + selective promotion at next observed recurrence.

## Audit cross-references

- **Pre-closure audit:** `tmp/PHASE3B_PRE_CLOSURE_AUDIT_2026-05-03.md`
- **Closure audit:** `tmp/PHASE3B_CLOSURE_AUDIT_2026-05-03.md`
- **9 questions for Marina (Q1-Q9):** all answered Phase A; defaults accepted
- **Sub-block CHANGES files:** 10 files in `reports/docs-architect/discovery/CHANGES_2026-05-0[2|3]_phase3b-5b*.md`

## BACKLOG entries

3 bundled entries created в this closure batch (Q6=(б) granularity):

- **BL-072** — Phase 3b Tier 1 production launch blockers (8 items)
- **BL-073** — Phase 3b Tier 2 production launch quality (7 items)
- **BL-074** — Phase 3b Tier 3 deferred work (22 items)

Each entry cross-references source closure CHANGES files. Phase 3c+ planning consults BACKLOG entries first.

## Phase 3b production launch blockers (Tier 1 reminder)

Production launch CANNOT ship until ALL 8 Tier 1 blockers resolved:

1. **T1.1** — Phase 3c transition wiring (`PlacementTransitionService.transition` invokes `LegalComplianceService.check_gates_for_transition`) — gate framework ready; integration pending. Per L39 / O.9 — protect from drive-by edits.
2. **T1.2** — 81 pre-existing test failures + 17 errors. PREDATES Phase 3b. Separate workstream from Phase 3c/4/5 deliverables (per audit O.2 — provenance preserved explicitly).
3. **T1.3** — Phase 5 PayoutCompliance wiring at `routers/payouts.py:create_payout`. Per audit O.3 — service is "claimed but not enforced" until Phase 5; callers MUST use `LegalComplianceService.check_gate()` for any G13-G18 lookups.
4. **T1.4** — G17 real body (счёт-фактура; НК РФ / Russian VAT compliance).
5. **T1.5** — G18 real body (real ORD provider; ФЗ-38 advertising compliance).
6. **T1.6** — G07 real body (supplementary agreement КЭП verification; ГК РФ ст.432 / КЭП legal validity).
7. **T1.7** — G15 real body (Act both-side КЭП verification).
8. **T1.8** — G16 real body (Мой налог real receipt issuance; ФЗ-Налог for self-employed).

Complete details в BL-072.

## Marina decisions (Q1-Q9)

| Q | Decision | Implication |
|---|---|---|
| Q1 | (а) `--no-ff` merge per CLAUDE.md project rule | Explicit Phase 3b boundary в history |
| Q2 | (а) Tag `v0.3.0-phase3b` at develop→main merge | Semantic versioning Phase 3b boundary marker |
| Q3 | (а) Minimal `IMPLEMENTATION_PLAN_ACTIVE.md` update | Status overlay + Branch HEADs only (no per-sub-block status table) |
| Q4 | (б) No CLAUDE.md lesson promotion | All L17-L39 lessons stay в closure-batch BACKLOG; promote selectively на observed recurrence |
| Q5 | (б) Preserve `feature/legal-compliance-gates @ 9d072f1` | Historical Phase 3a Foundation snapshot |
| Q6 | (б) 3 bundled BL entries (Tier 1 / Tier 2 / Tier 3) | Explicit cross-refs к sub-block CHANGES essential per O.8 |
| Q7 | (а) Preserve `feature/phase3b-compliance-gates` post-merge | Match precedent for sister branch retention |
| Q8 | (в) `PROJECT_KNOWLEDGE_v3.md` is project memory artifact | Audit prompt drift — IGNORE; not a repo file |
| Q9 | (а) Inline plan revision (L22 §3.B.1 + L25 §3.B.6) в closure-batch plan update | Per O.1 — defer twice = risk forgotten; cheap to fix while file open |

## Audit Возражения (O.1-O.9) dispositions

| # | Surface | Disposition |
|---|---|---|
| O.1 | Plan §3.B.1 + §3.B.6 are both "next plan revision" deferred — risk permanent forgetting | RESOLVED inline в closure-batch commit 3b.closure.1 (L22 §3.B.1 + L25 §3.B.6) per Q9=(а) |
| O.2 | T1.2 (81 pre-existing fails) is the only Tier 1 NOT a Phase 3b artifact | DOCUMENTED — BL-072 T1.2 explicitly cites "PREDATES Phase 3b. Separate workstream" |
| O.3 | `_GATE_CHECKERS` G13-G18 + `PayoutComplianceService` claim same partition (transitional fragile) | DOCUMENTED — BL-072 T1.3 explicitly notes "claimed but not enforced" until Phase 5; callers must use LegalComplianceService for G13-G18 |
| O.4 | `payout_service.create_payout` deferred 3× (5b.7a + 5b.7b + 5b.7c) — strong signal | DOCUMENTED — BL-073 T2.3/T2.4 explicitly notes "next time the file is touched, full cleanup mandatory per L33" |
| O.5 | Pragmatic `session.rollback()` requires CLAUDE.md S-48 contract decision, not localized fix | DOCUMENTED — BL-073 T2.2 escalated from "deferred to launch" → "S-48 contract decision needed before next bot-handler refactor session" |
| O.6 | Sister branch fully contained in develop — preservation is risk-free | CONFIRMED — Q5=(б) preserve at `9d072f1` |
| O.7 | `PROJECT_KNOWLEDGE_v3.md` doesn't exist в repo | RESOLVED — Q8=(в) project memory artifact, not a repo file. IGNORED per Marina |
| O.8 | 3-tier BL bundle trades discoverability against noise | MITIGATED — each BL entry explicitly cross-references source sub-block CHANGES files (BL-072/073/074 all cite specific closures) |
| O.9 | Phase 3c readiness — wiring missing from `placement_transition_service.py`; protect from drive-by edits | DOCUMENTED — BL-072 T1.1 explicitly notes "dedicated Phase 3c sub-block; do NOT inline into unrelated placement-transition refactors" |

All 9 Возражения either resolved inline or documented forward с explicit annotations (no "implicit deferral" — every concern surfaces in BACKLOG with provenance).

## Verification

| Gate | Pre-closure-batch (HEAD `402d7dc`) | Post-closure-batch (4 docs commits) |
|---|---|---|
| ruff (`src/`) | 4 errors | 4 (unchanged — docs only) |
| mypy (`src/`) | 10 errors | 10 |
| pytest unit | 62F / 642P / 1E | 62F / 642P / 1E |
| `make ci-local` | 81F / 922P / 6S / 17E | 81F / 922P / 6S / 17E |
| Alembic head | `e6a88faa9fa0` | unchanged |

## Out of scope (closure batch)

- Code-level changes (markers/bodies/hooks) — Phase 3b complete
- Phase 4 / Phase 5 / Phase 3c work — separate phases (see BL-072)
- 81 pre-existing test failures — separate workstream (T1.2 noted)
- Frontend updates — Tier 3 (BL-074)
- Master index for `reports/docs-architect/discovery/` — deferred (audit Q3 amendment)
- CLAUDE.md lesson promotion — deferred (Q4=(б))

## Phase 3b retrospective

The series shipped infrastructure as planned. Two open architectural surprises preserved to BACKLOG для Phase 3c/4/5 attention:

- **L39 / T1.1:** Framework readiness ≠ integration completion. Gate registries / dispatchers / markers all uniform at HEAD; only `PlacementTransitionService.transition()` enforcement wiring missing. Phase 3c can be small focused sub-block.
- **L33 / O.4 audit / T2.3+T2.4:** `payout_service.create_payout` dead code + S-48 violation deferred 3× across sub-blocks (5b.7a, 5b.7b, 5b.7c). Next-touch full cleanup mandatory per L33.

Both deliberately preserved with provenance so Phase 3c/4/5 work doesn't lose context.

🔍 Verified against: `f89934d` (post-closure.2 commit) | 📅 Updated: 2026-05-03
