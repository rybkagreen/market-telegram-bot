# CHANGES — Fix B: mistralai PyPI quarantine resolution (vendor wheel)

**Date:** 2026-05-12
**Branch:** feature/fix-b-mistralai-vendor
**Base:** develop @ 3803d89 (post-Fix-A merge)

## Closes

- **L71 interim gate Issue 1** — mistralai 1.12.4 PyPI quarantine blocks `docker compose build --no-cache`

## Decisions applied (per PROMPT_44 § Strategic context)

- **Option (b) Vendor wheel** — chosen за self-containment под Marina's архитектурная чистота criteria
- **Q1 = Yes** — offline-buildable repo standard
- **Q2 = Drop mistralai_azure / mistralai_gcp** companions — intent applied; *partially achieved* (see § Surprises 1)
- **Q3 = Defer** mistralai 1.x → 2.x upgrade (BL-102 candidate)
- **Q4 = Defer** other quarantined packages audit (BL-101 candidate)

## Summary

Vendored `mistralai-1.12.4-py3-none-any.whl` (509319 bytes, ~500 KB) к
`vendor/wheels/`. `pyproject.toml` switched к Poetry path-style dependency.
`poetry.lock` regenerated с minimal scope (only mistralai entry + content
hash + Poetry version metadata changed; NO other packages affected).

Discovered during Šaг 4 fresh build: 4 Dockerfiles (api, bot, worker,
api-contract) COPY only `pyproject.toml` + `poetry.lock*` к build context —
not `vendor/`. Added `COPY vendor/ ./vendor/` к both builder и final stages
of all 4 Dockerfiles per path dep resolution requirement.

Fresh `docker compose down -v && docker compose build --no-cache` now exits 0.
All 8 images built. Containers up, `mistralai 1.12.4` imports clean в API +
worker_critical containers. /docs, /health, /openapi.json все 200.

## Files touched

- `vendor/wheels/mistralai-1.12.4-py3-none-any.whl` — **NEW** (509319 bytes / 500 KB vendored binary)
- `vendor/wheels/` — **NEW directory**
- `.gitignore` — exception added: `!vendor/wheels/` + `!vendor/wheels/*.whl` (overrides global `wheels/` exclude on line 22)
- `pyproject.toml` — `mistralai = { path = "vendor/wheels/mistralai-1.12.4-py3-none-any.whl" }` (was `mistralai = "^1.12.4"`)
- `poetry.lock` — mistralai entry: file-source + new SHA256; content hash updated; Poetry generator version 2.3.4 → 2.4.0. NO other packages affected
- `docker/Dockerfile.api` — `COPY vendor/ ./vendor/` added в builder stage (after pyproject COPY) + final stage (after pyproject COPY)
- `docker/Dockerfile.bot` — same pattern: builder + final stage
- `docker/Dockerfile.worker` — same pattern: builder + final stage
- `docker/Dockerfile.api-contract` — same pattern: builder + final stage
- `reports/docs-architect/discovery/CHANGES_2026-05-12_fix-b-mistralai-vendor.md` — this file

## Commits (chronological)

| SHA | Subject |
|---|---|
| `09f560c` | chore(deps): vendor mistralai-1.12.4 wheel за PyPI quarantine |
| `094e90a` | build(deps): switch mistralai к vendored wheel path |
| `c48d326` | chore(docker): COPY vendor/ к build context для path dep resolution |
| `<TBD>` | docs(fix-b): closure CHANGES (this commit) |

## Verification

### Fresh build (Šaг 4)
```
docker compose down -v && docker compose build --no-cache
```
Exit code 0. All 8 images built: api, bot, worker_critical, worker_background,
worker_game, celery_beat, flower, nginx. No `Unable to find installation
candidates` errors. No PyPI 404s.

### Smoke check (Šaг 5)
```
docker compose exec api python -c 'import mistralai; print(mistralai.__version__)'
→ 1.12.4

docker compose exec worker_critical python -c 'import mistralai; print(mistralai.__version__)'
→ 1.12.4

curl http://localhost:8001/health → 200
curl http://localhost:8001/docs → 200
curl http://localhost:8001/openapi.json → 200
```

No startup errors. No tracebacks. mistralai import-time resolution works.

### Baselines (L72 single run)
| Gate | Result |
|---|---|
| format-check | 0 errors / 400 files |
| lint | 7 errors (BL-024 baseline) |
| typecheck | 0 errors / 291 files |
| pytest | 1018 passed / 2 skipped / 0 failed / 0 errored |
| ci-local exit | 1 (lint-only per BL-024) |

## Wheel provenance

- **Source:** Built locally from official GitHub source `mistralai/client-python` @ tag `v1.12.4`
- **Build environment:** cached `market-telegram-bot-api:latest` image (Python 3.14.4, pip 26.0.1) с command `pip wheel . --no-deps -w /wheels/`
- **Filename:** `mistralai-1.12.4-py3-none-any.whl`
- **Size:** 509319 bytes (~500 KB compressed)
- **SHA256:** `2fc831ed5ba0559f41627dee35d8410cdfc0b021d62e2afa97b2c878bb1722f8`
- **Wheel tag:** `py3-none-any` (universal pure Python, no compiled extensions)
- **NB:** SHA256 differs от original PyPI wheel (`7b69fcbc306436491ad3377fbdead527c9f3a0ce145ec029bf04c6308ff2cca6`) — fresh local build от same source. Functionally identical; hash differs due к pip metadata + build timestamp embedded в wheel.

## Surprises log (BL-026)

1. **Companion packages `mistralai_azure` + `mistralai_gcp` bundled внутри same wheel** —
   PROMPT_43 probe noted они present в cached image и assumed они were
   transitive deps drop-able by removing from pyproject. Reality: github
   `mistralai/client-python` repo has `packages/mistralai_azure/` +
   `packages/mistralai_gcp/` directories, and the wheel build includes them
   all три packages as top-level modules. Q2 "drop companions" partially
   achieved — они no longer listed as separate poetry deps (were never direct
   deps), но они still installed by single mistralai wheel. To truly drop
   would require custom wheel build excluding `packages/azure` + `packages/gcp`
   from source — out of scope for Fix B impl. Companion packages remain
   dormant (not imported anywhere в src/, ~1 MB extra disk).

2. **Dockerfile COPY vendor/ требование** — PROMPT_44 анticipated pyproject +
   poetry.lock updates plus vendor/ commit, но не предусмотрел 4 Dockerfiles
   COPY only pyproject + poetry.lock к build context. Build failed в Šaг 4
   с `Path /app/vendor/wheels/mistralai-... does not exist`. Fix scoped к
   adding `COPY vendor/ ./vendor/` в builder + final stages of all 4
   Dockerfiles. Necessary для Fix B path dep к actually работать; NOT scope
   creep — only single COPY line added per Dockerfile, no logic changes.

3. **Poetry version 2.3.4 → 2.4.0** в lock file — container image has Poetry
   2.4.0, develop's lock file was generated by 2.3.4. Lock regen bumps
   generator metadata. Benign — same lock format, same resolution behavior.

4. **Wheel SHA256 differs от PyPI original** — pure-Python wheels are not
   bit-for-bit reproducible due to pip metadata + build timestamps. Our
   fresh build from same v1.12.4 git tag produced different bytes than
   original PyPI wheel. Functionally identical (same source code). Documented
   here for audit transparency.

## Not included / deferred

- mistralai 1.x → 2.x upgrade (BL-102 candidate, Q3 defer)
- Other quarantined PyPI packages audit (BL-101 candidate, Q4 defer)
- Custom wheel build to truly drop mistralai_azure / mistralai_gcp (см. Surprise 1 — BL-103 candidate если Marina wants surgical drop)
- BL-080 8c merge cycle — next: PROMPT_45 merge develop, then PROMPT_46/47/48 для 8c branch catch-up + L71 re-verify + 8c merge
- GlitchTip DB provisioning (BL-099 candidate, cosmetic, L71 Issue 3)
- BACKLOG.md updates (batched к Phase 3 closure)

🔍 Verified against: feature/fix-b-mistralai-vendor HEAD (pending closure commit)
📅 Updated: 2026-05-12
