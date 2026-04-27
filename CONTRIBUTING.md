# Contributing

## CI / Verification Gate

GitHub Actions are not currently available for this repository (account-level
billing constraint, see BL-017). The verification gate is therefore **local**:

```bash
make ci-local
```

This runs:

- `ruff check` (lint)
- `ruff format --check` (format)
- `mypy src/` (type check)
- `pytest tests/` (full suite, excluding `e2e_api` which requires
  `docker-compose.test.yml` stack, and `tests/unit/test_main_menu.py`
  which has a known collection error)

Run `make ci-local` before opening a PR or merging into `develop` / `main`.

**Baseline:** as of 2026-04-26 (commit d5075ab), `make ci-local` produces
≈10 mypy errors / ≈12 ruff warnings / ≈82 failed + 35 errored tests. These
are pre-existing and tracked in `reports/docs-architect/typecheck_baseline.md`,
BL-007 (ruff), and BL-019 (test debt). The gate is **"no new regressions
relative to baseline"**, not "all green", until those backlog items resolve.

If you cannot run `make ci-local` locally (e.g., container memory pressure
per BL-008 historical entry — invalidated 2026-04-26 but workflow OOM
remains a theoretical concern on smaller hosts), document why in the PR
and run target subsets (`tests/unit/`, `tests/integration/`, `tests/tasks/`)
sequentially.
