# POST v0.2.0 Lessons — 2026-05-01

Cycle: pre-flight → `BOT_API_HMAC_SECRET` investigation → celery_beat ops fix → release v0.2.0.

## L1 — Env snapshot drift как явная failure category (D5)

Pydantic `ValidationError` на required field в running container ≠ всегда code/config bug. Compose `env_file` snapshot at container creation time; `restart` НЕ re-reads `.env`. Только `up -d` (config drift detected) либо `--force-recreate` обновляет env snapshot.

Pattern: container created в момент N-1, `.env` updated в момент N, code added required field в момент N (между N-1 и N container snapshot). Validation fail at startup → restart loop indefinitely.

Investigation D1-D4 framework миссировал эту категорию. Future investigation prompts для startup ValidationError должны включать "container env snapshot timing" как explicit candidate.

Recovery: targeted `docker compose up -d --force-recreate --no-deps <service>`. **Не** global force-recreate (cascade risk).

Concrete instance: BL-066 (`BOT_API_HMAC_SECRET` introduced 2026-05-01 08:07; `.env` updated 08:17; celery_beat container created 2026-04-28 → 8 hours restart loop until detected in pre-flight).

## L2 — Pydantic ValidationError input_value disclosure

`pydantic_core._pydantic_core.ValidationError` echoes other env values в `input_value={...}` part of error message. В celery_beat logs visible `BOT_TOKEN` (truncated, partially exposed).

Surface: any container logs где `Settings()` instantiation fails. Если operators имеют read access к Docker logs — secret partial leak.

Candidate process item (defer to Phase 3 closure): redact либо filter `input_value` в startup `ValidationError` logging. Custom error formatter либо log filter в container entrypoint.

## L3 — CHANGELOG warning false positive on feature branches

Stop-hook fires CHANGELOG warning regardless of branch context. Feature branches accumulate work-in-progress; CHANGELOG entry имеет смысл только на `develop` либо `main`. Current behaviour creates noise.

Proposed: hook checks `git branch --show-current`; CHANGELOG warning only on `develop`/`main`. CHANGES warning continues on all branches но exempts research-only / docstring-only commits.

## L4 — Verification protocol observations

Lessons из 17.3 cycle и текущего hygiene:

- "Consumer existence" ≠ "consumer usage". Trace data flow до actual call sites, не stop на definition existence (false-positive в Шаг 0 17.3b).
- Revisit prior research notes на ту же surface ПЕРЕД грепом. `RESEARCH_17-3_credits_inventory_2026-05-01.md:230` уже flagged dead endpoint, был пропущен.
- Не trust hook/STOP report wording буквально (BL-067 `alembic.docker.ini` lesson).
- Type 4 HARD STOP в research phase — design works, ловит ошибки до mutation.

Apply: investigation prompts должны включать "Шаг 0: revisit prior research notes" если surface уже была discovered ранее.

## L5 — BL-024 evidence drift

`test_gamification InvalidRequestError: A transaction is already begun on this Session` — reason изменился post-17.3a (`xp_service` `session.begin()` теперь vs conftest pre-started session, не просто missing transaction context). Counter не сдвинулся (76 failed остался stable), но root-cause description в BL-024 stale.

Candidate process item (defer to Phase 3 closure): refresh BL-024 reason field.

## L6 — Investigation framework D1-D4 incomplete

Pre-flight investigation template имел 4 diagnostic categories:
- D1: missing from `.env.example` artifact
- D2: ops sync gap
- D3: pre-existing latent
- D4: bad value validation

Agent surfaced D5 (env snapshot drift) — категория не была в framework. Future investigation templates для startup failures должны include "container snapshot vs host file drift" как explicit D5 slot.

## L7 — Handoff terminology hygiene

Handoff 2026-05-01 evening:
- claimed `develop = c30d2d6` / +8 commits over main; reality `9981e8d` / +13 commits (sprint closure docs landed после написания handoff)
- claimed "FF-mergeable"; реально diverged по structure (merge-base ≠ HEADs), `--no-ff` обязателен; "no merge conflicts" корректное wording
- referenced `docker-compose.dev.yml` / `.prod.yml`; repo имеет только `docker-compose.yml` + `docker-compose.test.yml`

Future handoffs: empirical re-verify HEAD'ов перед написанием; "FF-mergeable" использовать строго; не predict file paths которые могут не существовать.

## Process candidates (для Phase 3 closure batch)

- Hook noise (L3) — CHANGELOG warning branch-aware; CHANGES warning exempts research/docstring commits.
- Verification protocol (L4) — trace data flow до call sites; revisit prior research notes pre-grep.
- BL-024 evidence refresh (L5) — root cause description update.
- ValidationError disclosure (L2) — log redaction для startup validation errors.
- Investigation framework expansion (L6) — D5 slot для container snapshot drift.

---

Reference: pre-flight отчёт, investigation отчёт, ops fix отчёт, release отчёт (все в session transcripts; сохраняются на planner side, не в repo).
