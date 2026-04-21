# Web Portal — E2E Tests (Playwright)

End-to-end smoke & regression suite for `web_portal/`. Tests run in an
**isolated Docker stack** against a production-like nginx → FastAPI →
PostgreSQL → Redis runtime, seeded with deterministic fixtures.

## Architecture

```
postgres-test  ───┐
redis-test     ───┤
                  ├─── seed-test (one-shot: migrations + fixtures)
                  │          │
                  │          ▼
                  └─── api-test (ENV=testing, mounts /api/auth/e2e-login)
                               │
                               ▼
                         nginx-test (port 80, no SSL)
                               │
                               ▼
                          playwright (container, runs the suite)
```

Test data comes from `scripts/e2e/seed_e2e.py` — creates 3 users
(advertiser/owner/admin), one channel, and a couple of placement requests.

## Auth bypass

In real use, login goes through the Telegram widget or a 6-digit OTP from the
bot — neither works in a container. When `ENVIRONMENT=testing` the API mounts
one extra endpoint:

```
POST /api/auth/e2e-login  { "telegram_id": 9001 }  → { access_token, user }
```

It **never** mounts in dev/staging/prod (guarded in `src/api/main.py`), so it
is not an attack surface outside the isolated compose stack.

`tests/global-setup.ts` calls this endpoint once per role and writes the JWT
into Playwright `storageState` files under `tests/.auth/` — each spec loads
the appropriate state and skips the login screen.

## Running locally

First-time setup:
```bash
cp .env.test.example .env.test    # committed template — customise only if needed
```

Then:
```bash
make test-e2e        # build, run, tear down — single command, CI-ready
```

Or for iterative local work (stack stays up, re-run suite manually):

```bash
make test-e2e-up                      # start stack
docker compose -f docker-compose.test.yml --env-file .env.test \
    run --rm playwright npx playwright test --project=desktop-chromium
make test-e2e-down                    # tear down when finished
```

## Visual regression

`specs/visual.spec.ts` captures a full-page PNG per route × viewport and
diffs against committed baselines under `tests/visual-snapshots/`.

**After intentional UI changes**, refresh baselines:

```bash
make test-e2e-visual-update    # regenerates, commit the resulting PNGs
git add web_portal/tests/visual-snapshots/ && git commit -m "chore(visual): refresh baselines for <change>"
```

Dynamic content (timestamps, balances, relative-time) is masked via
`data-testid` selectors in the spec so those regions don't cause false
positives. If you introduce new dynamic UI, add a matching `data-testid`
to the element and extend the `masks` array.

Thresholds (`playwright.config.ts`):
- `threshold: 0.2` — per-pixel RGB tolerance (absorbs sub-pixel AA noise).
- `maxDiffPixelRatio: 0.005` — up to 0.5% of pixels may differ without
  failing. On 1440×900 that's ~6500 px — enough to ignore font-rendering
  jitter, too few to hide a real layout shift.

## What the smoke test checks

For every protected route × 3 viewports (iPhone SE, Pixel 5, 1440×900) in
`tests/specs/smoke.spec.ts`:

1. **HTTP 200** from the SPA shell.
2. **Exactly zero or one** breadcrumbs `<nav aria-label="Хлебные крошки">`
   (regression: S-47 in-screen duplicate fix).
3. **No horizontal overflow** — `scrollWidth ≤ clientWidth`.
4. **No external sprite refs** — `<svg class="rh-icon"><use href="...">` must
   be a local `#id` fragment, never an absolute URL (regression: icon sprite
   inlining).
5. **No uncaught client errors** (`pageerror` / `console.error`).
6. **axe-core WCAG AA baseline** — violations logged as annotations (not
   failing yet; will be promoted to an assertion when the backlog is clean).

## Adding a spec

1. Add route specs to `tests/fixtures/routes.ts` — choose the role that can
   reach the route without a 403.
2. For deep flows (wizards, form submits, etc.), add a new spec file under
   `tests/specs/` and use `test.use({ storageState: role.storageFile })` to
   authenticate.
3. If the flow needs extra test data, extend `scripts/e2e/seed_e2e.py` — keep
   it idempotent.

## Reports

After a run, artifacts land in `reports/e2e/`:
- `html/` — `npx playwright show-report reports/e2e/html` for interactive view
- `results.json` — machine-readable results (for CI diffs)
- `artifacts/` — trace files, screenshots, videos from failures

## CI

The stack is designed to run unchanged in CI — `make test-e2e` exits with
the Playwright exit code and always tears down via the `||` chain.
Recommended GitHub Actions step:

```yaml
- name: E2E smoke
  run: make test-e2e
- name: Upload report
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: playwright-report
    path: reports/e2e/
```

## Known limitations

- `webkit` in Docker emulates Safari but is **not bit-identical** — iOS-only
  bugs (especially around `dvh`, `oklch()`, or `-webkit-*` prefixes) still
  need manual verification on a real device.
- Admin routes depend on seeded admin state. If you add a route requiring
  additional fixtures, extend the seed.
- The suite is single-worker (`workers: 1`) because the seed is not
  reset between tests — keep specs read-only or reset state yourself.
