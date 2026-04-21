# CHANGES — Phase 8.1 hardening, iteration 3: visual regression baseline

Adds pixel-diff visual regression to the Playwright suite. Catches
structural and styling regressions that route-sweep + API contract don't —
layout shifts, colour drift, missing padding, broken empty states, font
fallback flashes, etc.

## Files added

- `web_portal/tests/specs/visual.spec.ts` — one full-page screenshot per
  route × 3 viewports (105 total). Masks dynamic selectors so timestamps
  and balances can't cause false positives.
- `web_portal/tests/visual-snapshots/` — 105 committed baseline PNGs
  (5.3 MB). Path template:
  `visual-snapshots/visual.spec.ts-snapshots/<route>-<projectName>.png`.

## Files changed

- `web_portal/tests/playwright.config.ts`:
  - `expect.toHaveScreenshot`: `threshold: 0.2` (per-pixel RGB tolerance,
    absorbs anti-aliasing), `maxDiffPixelRatio: 0.005` (0.5% of pixels may
    differ — ≈6500 px on a 1440×900 page; enough to hide font-rendering
    jitter, too few to hide a real layout shift), `animations: 'disabled'`.
  - `snapshotDir` + `snapshotPathTemplate` — keeps baselines under a
    predictable, project-scoped path so mobile-webkit comparisons don't
    leak into mobile-chromium.
- `web_portal/tests/.gitignore` — ignores `*-actual.png` / `*-diff.png`
  (written alongside baselines on failure). Baselines themselves **are**
  committed; they're the source of truth.
- `Makefile` — new target `make test-e2e-visual-update` — refreshes
  baselines in one shot (use after intentional UI changes; commit the
  resulting PNGs).
- `web_portal/tests/README.md` — visual regression workflow.

## Determinism — what's pinned

- Playwright version: `1.59.1` (both the `@playwright/test` dep and the
  `mcr.microsoft.com/playwright:v1.59.1-jammy` Docker tag).
- Locale: `ru-RU`.
- Timezone: `Europe/Moscow`.
- `prefers-reduced-motion` forced to `reduce` via `emulateMedia`.
- `document.fonts.ready` awaited before capture.
- `networkidle` wait before capture.
- Containers use tmpfs volumes → each seed run is identical.

## Masking rules

Selectors whose text is expected to vary run-to-run are masked (Playwright
paints them flat before diffing):

| selector                            | reason                         |
| ----------------------------------- | ------------------------------ |
| `[data-testid="balance"]`           | user balance rendering         |
| `[data-testid="user-balance"]`      | sidebar user-balance chip      |
| `time[datetime]`                    | any `<time>` element           |
| `[data-testid="relative-time"]`     | "5 min ago" labels             |
| `[data-testid="timestamp"]`         | absolute timestamps            |

When adding new dynamic UI, add the relevant `data-testid` and extend the
`masks` array in `visual.spec.ts`.

## Usage

```bash
# Verify against baselines (part of the main CI run).
make test-e2e

# Refresh baselines after intentional UI change.
make test-e2e-visual-update
git add web_portal/tests/visual-snapshots/
git commit -m "chore(visual): refresh baselines for <change>"
```

## Contract

No public API contract changed. This is a pure test-tooling addition.

## Regression surface

- 105 visual tests now run as part of `make test-e2e`, ~5 min
  incremental. Total suite time: ~10 min (API contract + smoke + visual).
- First-pass baseline run produced zero skipped tests — every seed screen
  rendered enough to capture. No route-specific masking needed beyond
  the global `data-testid` list.

## Known limitations

- Font metrics between Chromium and WebKit differ slightly; the two
  projects have independent baselines. No cross-browser pixel parity.
- On a macOS dev machine the Docker-captured baselines still rule —
  don't run Playwright natively; use the image so rendering stays stable.
- Baselines grow with the route count. At 5.3 MB for 105 screens, git
  can handle it; at 10× that it'd be worth moving to git-lfs.

---
🔍 Verified against: f158495..HEAD | 📅 Updated: 2026-04-20T12:30:00+03:00
