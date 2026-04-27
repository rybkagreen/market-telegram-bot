# CHANGES — 2026-04-26 — Workflow cleanup + local CI gate + production sync

## Summary

Phase 2 prep cleanup: dead GitHub Actions workflows removed/disabled,
local CI gate established as primary verification mechanism, production
containers rebuilt to match `main @ d5075ab`. Bundles the deferred
CHANGES + CHANGELOG entry for plan-08 reference fix (commit `7db453d`,
Промт-2.5) per BL-013 protocol option (b).

## Workflow changes

### Deleted
- `.github/workflows/deploy.yml` — 0 successful runs across all history.
  References nonexistent `/path/to/market-telegram-bot` placeholder,
  nonexistent `docker-compose.prod.yml`, nonexistent `worker` service.
  Never functional. Removal eliminates noise in GH Actions UI.

### Disabled (renamed)
- `.github/workflows/contract-check.yml` → `contract-check.yml.disabled`
- `.github/workflows/frontend.yml` → `frontend.yml.disabled`

Both technically valid workflows, but unable to run since 2026-03-04
billing block. Per BL-017 update, GH Actions billing not being restored.
Renamed to preserve code for unlikely future revival without leaving
them spamming the Actions UI with "billing locked" failures on every
push.

### Untouched
- `.github/workflows/ci.yml.disabled` — already disabled, kept as-is.

## Local CI gate

Added `make ci-local` Makefile target — runs lint + format check + mypy
+ pytest. Documented in `CONTRIBUTING.md` as the de-facto verification
gate. Baseline numbers (mypy 10/5/273, ruff 12, pytest 82F/35E)
documented inline.

## Plan-08 reference fix (deferred from Промт-2.5)

Commit `7db453d` fixed a fabricated `plan-08 backlog` reference in
`IMPLEMENTATION_PLAN_ACTIVE.md` Decision 5 (Phase 2 § 2.B.0). Replaced
with reference to `BL-014` (correlation_id middleware wiring) which was
added to BACKLOG.md in working tree.

The CHANGES entry was deferred per BL-013 stop-hook relay decision (b)
to bundle into next natural commit. This is that bundle. No standalone
CHANGES file for `7db453d` is needed — it's documented here.

## Production sync

`docker compose up -d --build` executed at end of this prompt to
rebuild all images from `main @ d5075ab` and restart containers.
Closes drift between git state (T1-3, T1-7 hotfixes merged 2026-04-26
12:03) and running container images (previously built 2026-04-21..25).

## Public contract delta

None.
- Workflow changes are CI/infrastructure only — no API / schema /
  behaviour change.
- Local CI target is dev tooling — no contract.
- Plan-08 fix is plan document only — no code delta.
- Production rebuild from same git state — no delta beyond what
  was already merged (T1-3 + T1-7 in main since 2026-04-26 12:03).

## Origins

- BL-017 update.
- BL-013 protocol option (b) — Промт-2.5 stop-hook deferred to natural
  commit.
- PROD_STATE_OBSERVATION_2026-04-26.md (Промт-2.A) — empirical
  evidence for workflow decisions.
- User decisions in Промт-2.B kickoff (billing not restoring,
  delete deploy.yml, rename rest, accept local CI as permanent gate).

🔍 Verified against: 7db453d | 📅 Updated: 2026-04-26T20:00:00+03:00
