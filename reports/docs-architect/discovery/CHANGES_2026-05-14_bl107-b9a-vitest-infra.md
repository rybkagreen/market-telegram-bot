# CHANGES 2026-05-14 — BL-107 Phase B.9 Phase A (vitest infrastructure)

## Context

Phase B.5b shipped 3 new BL-107 frontend screens (web_portal:
`AdminChannelVerificationsList`, `AdminChannelVerificationDetail`;
mini_app: `OwnSubmitRegistryEvidence`) без accompanying component tests
because neither frontend had vitest configured. Phase B.9 is the test
coverage closure phase; Phase A здесь sets up the missing infrastructure.

**Scope envelope:** narrow infra bootstrap — install pinned vitest+RTL
deps, create per-frontend `vitest.config.ts` + setup file + smoke test +
test-only tsconfig. No business logic touched, no migrations, no API
changes, no component changes.

Built atop Phase B.8 (`d8da720`).

## Empirical decisions

1. **Per-frontend vitest config** (not shared package) — keeps frontends
   independent per existing convention. Each `vitest.config.ts` does
   `mergeConfig(viteConfig, defineConfig({test: {...}}))` to reuse Vite
   plugins/aliases.

2. **jsdom over happy-dom** — jsdom is the conservative default and matches
   what `@testing-library/react` documentation recommends. happy-dom is
   faster but has historically had React-19 compatibility hiccups.

3. **`globals: false`** (explicit imports `from 'vitest'`) — avoids ESLint
   config rewrite for `describe`/`it`/`expect` globals and plays cleanly
   with `verbatimModuleSyntax: true` in tsconfig.app.json. Test files do
   `import { describe, it, expect, vi } from 'vitest'` per file.

4. **Separate `tsconfig.test.json`** (not just exclude-from-app) — required
   because:
   - `tsconfig.app.json` has `noUnusedLocals: true` and `noUnusedParameters: true`,
     which would fail tsc-check on test files (e.g. unused render destructure)
   - `@testing-library/jest-dom` extends Vitest's `Assertion` interface; this
     augmentation is only seen by tsc if the package is in `compilerOptions.types`
   - `tsconfig.test.json` extends `tsconfig.app.json`, overrides unused-vars to
     `false`, adds `@testing-library/jest-dom` to `types`, includes only test
     files

   `tsconfig.json` root references all three (`app`, `node`, `test`) — `tsc -b`
   builds them all, each `noEmit: true`, no output conflict.

5. **`tsconfig.app.json` exclude clause added** — `src/**/*.test.{ts,tsx}`,
   `src/**/*.spec.{ts,tsx}`, `src/test/**`. Prevents app build from
   tsc-checking test files.

6. **Triple-slash reference for vitest/config removed** —
   `@typescript-eslint/triple-slash-reference` flagged it; vitest 4
   auto-extends Vite config types via `import from 'vitest/config'`, so the
   reference was redundant anyway.

## Changes per file

### web_portal

**New:**
- `web_portal/vitest.config.ts` — `mergeConfig` with vite config, jsdom env,
  setupFiles, includes pattern, explicit alias mirror
- `web_portal/tsconfig.test.json` — extends app config, adds jest-dom types,
  relaxes unused-vars
- `web_portal/src/test/setup.ts` — single line `import '@testing-library/jest-dom/vitest'`
- `web_portal/src/test/smoke.test.tsx` — render+toHaveTextContent assertion

**Modified:**
- `web_portal/package.json` — added 6 devDeps (vitest@4.1.6,
  @testing-library/react@16.3.2, @testing-library/jest-dom@6.9.1,
  @testing-library/user-event@14.6.1, jsdom@29.1.1, @vitest/ui@4.1.6) +
  3 scripts (`test`, `test:run`, `test:ui`)
- `web_portal/package-lock.json` — lockfile updated
- `web_portal/tsconfig.app.json` — added `exclude` clause
- `web_portal/tsconfig.json` — added `tsconfig.test.json` reference

### mini_app

Same set of changes mirrored:

**New:**
- `mini_app/vitest.config.ts`
- `mini_app/tsconfig.test.json`
- `mini_app/src/test/setup.ts`
- `mini_app/src/test/smoke.test.tsx`

**Modified:**
- `mini_app/package.json` — same 6 devDeps + 3 scripts
- `mini_app/package-lock.json`
- `mini_app/tsconfig.app.json`
- `mini_app/tsconfig.json`

## Versions pinned (BL-117 supply-chain hygiene)

All 6 deps installed with explicit version (no `^` at install time;
npm wrote `^` prefix into package.json after pinning — это standard npm
behavior, lockfile pins to exact 4.1.6/16.3.2/etc.):

| Package | Version |
|---|---|
| `vitest` | 4.1.6 |
| `@testing-library/react` | 16.3.2 |
| `@testing-library/jest-dom` | 6.9.1 |
| `@testing-library/user-event` | 14.6.1 |
| `jsdom` | 29.1.1 |
| `@vitest/ui` | 4.1.6 |

## Verification gates

| Gate | web_portal | mini_app |
|---|---|---|
| `npm run test:run` (smoke) | ✅ 1 passed | ✅ 1 passed |
| `npm run build` (tsc + vite) | ✅ built | ✅ built |
| `npx eslint vitest.config.ts src/test/` | ✅ clean | ✅ clean |

Pre-existing ESLint baseline errors (in `AIInsightCard.tsx` etc.) untouched —
out of B.9 scope per Principle 1.

## Forced scope

None. ESLint config not modified. Build pipeline unchanged. No new BL
candidates surfaced.

## Deferred to production launch

None — this is test infra, not production code.

## Next sub-block

Phase B (component tests) — ≥3 tests each for 3 BL-107 screens using the
new infrastructure.

🔍 Verified against: `d8da720` (Phase B.8 HEAD) | 📅 Updated: 2026-05-14T20:34:00Z
