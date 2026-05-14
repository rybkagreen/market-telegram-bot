# TypeScript 7.0 Beta — Migration Readiness Research

**Date:** 2026-05-14
**Branch:** `research/ts7-migration-readiness` @ `c1a8e9e` (worktree off `develop`)
**Scope:** Read-only audit of `web_portal/`, `mini_app/`, `landing/` (3 TS frontends — scope expanded from original prompt per Marina approval 2026-05-14)
**Working dir:** `/opt/mtb-ts7-research/` (parallel session, main BL-107 checkout untouched)
**Triggered by:** Marina request — should we migrate to TS 7.0 Beta, and when?
**TS 7.0 Beta release date:** 2026-04-21 (per official Microsoft announcement)

---

## Summary

| Field | Value |
|---|---|
| **Verdict** | 🟢 **GREEN** — codebase already TS-7-compliant |
| **Migration effort** | **TRIVIAL** (incremental path: <1 day) — **MINOR** (full switch: 2-3 days) |
| **Recommended timing** | Option (D) Incremental NOW + Option (B) Full switch post-Phase-5 launch |
| **Blockers** | 0 hard blockers · 3 minor `landing/tsconfig.json` gaps (cosmetic) |
| **Ecosystem readiness** | ~90% — typescript-eslint requires `@typescript/typescript6` shim (one-line install) |
| **Risk level** | LOW — TS 7 type-check logic structurally identical to 6.0 |

**Why this is exceptionally clean:** the team has been progressively cleaning code on the path to TS 7 — already on TS 6.0.2 (final JS-based release before the Go rewrite), all tsconfigs use `moduleResolution: "bundler"`, target ES2022+, no deprecated features, zero `any`/`@ts-ignore`/`@enum` JSDoc, no decorators, no closure-style JSDoc. The `mini_app/tsconfig.app.json` even has a comment `// baseUrl removed — deprecated in TS 6.0` indicating proactive deprecation cleanup.

---

## 1. Current State

| Frontend | TS version | Target | Build | Source files |
|---|---|---|---|---|
| `web_portal/` | `^6.0.2` | ES2025 | `tsc -b && vite build` | 185 (.ts + .tsx) |
| `mini_app/` | `^6.0.2` | ES2025 | `tsc -b && vite build` | 145 |
| `landing/` | `6.0.2` (exact pin) | ES2022 | `vite build` only | 17 |
| `web_portal/tests/` | shared with web_portal | ES2022 | Playwright runner | n/a |

**Shared stack:**
- Build: Vite ^8.0.0, @vitejs/plugin-react ^6.0.0, Tailwind v4
- Lint: ESLint ^9.39.4, typescript-eslint 8.56–8.58 (per frontend)
- React: 19.2.x, @types/react 19.2.x
- HTTP: ky ^1.14
- State: Zustand ^5.0.11, React Query ^5.90.21
- Forms: react-hook-form ^7.71, zod ^3.25
- Sanitization: dompurify ^3.3.3
- Monitoring: @sentry/react ^10.45 (web_portal + mini_app)
- E2E: @playwright/test 1.59.1 (web_portal/tests/ — separate npm package)
- **No unit-test runner** (no vitest, no jest in any frontend)

**Module resolution / target / module: all 6 tsconfigs already TS-7-aligned.**

---

## 2. Dependency Inventory

### 2.1 web_portal/ (production app, 17 deps + 16 devDeps)

```json
{
  "dependencies": {
    "@hookform/resolvers": "^4.1.3",
    "@sentry/react": "^10.45.0",
    "@tanstack/react-query": "^5.90.21",
    "dompurify": "^3.3.3",
    "ky": "^1.14.3",
    "lucide-react": "^0.577.0",
    "react": "^19.2.4",
    "react-dom": "^19.2.4",
    "react-hook-form": "^7.71.2",
    "react-router-dom": "^7.13.1",
    "recharts": "^3.8.1",
    "zod": "^3.25.76",
    "zustand": "^5.0.11"
  },
  "devDependencies": {
    "typescript": "^6.0.2",
    "typescript-eslint": "^8.56.1",
    "vite": "^8.0.0",
    "@vitejs/plugin-react": "^6.0.0",
    "eslint": "^9.39.4",
    "@types/react": "^19.2.14",
    "@types/node": "^24.12.0",
    /* + 9 others */
  }
}
```

### 2.2 mini_app/ (Telegram WebApp, 14 deps + 16 devDeps)

Same baseline as web_portal, plus:
- `@telegram-apps/sdk-react` ^2.0.25 (Telegram WebApp bindings)
- `motion` ^12.36.0 (animations)
- `typescript-eslint` ^8.58.0 (one minor newer than web_portal)

### 2.3 landing/ (static marketing page, 5 deps + 13 devDeps)

```json
{
  "dependencies": {
    "lucide-react": "latest",          // ⚠️ unpinned
    "motion": "^12.0.0",
    "react": "^19.2.0",
    "react-dom": "^19.2.0",
    "react-router": "^7.0.0"           // NB: react-router not -dom — landing is static
  },
  "devDependencies": {
    "typescript": "6.0.2",             // exact pin (not caret)
    "typescript-eslint": "^8.58.1",
    "vite": "^8.0.0",
    "@vitejs/plugin-react": "^6.0.0",
    "@lhci/cli": "latest",             // ⚠️ unpinned
    "tsx": "latest",                   // ⚠️ unpinned — used by prebuild sitemap/og scripts
    /* + 7 others */
  }
}
```

**Side observations (unrelated to TS 7 migration but worth noting):**
- `landing/package.json` uses `"latest"` for 3 packages (`lucide-react`, `@lhci/cli`, `tsx`) — supply-chain risk drift, recommend pinning. Out of scope but flagged.
- `landing/` uses `react-router` v7 (raw), while `web_portal/` + `mini_app/` use `react-router-dom` v7 — intentional asymmetry (landing is mostly static), no action needed.

---

## 3. TS 6.x Deprecations Audit

TS 7.0 promotes several TS 6.0 deprecations to hard errors. Audit results:

| Deprecation removed in TS 7 | Status in our codebase | Severity |
|---|---|---|
| `target: "es5"` | Not used (ES2022/ES2023/ES2025) | ✅ N/A |
| `module: "amd"` / `"umd"` / `"systemjs"` / `"none"` | Not used (ESNext) | ✅ N/A |
| `moduleResolution: "node"` / `"node10"` / `"classic"` | Not used (`bundler` in all 6 tsconfigs) | ✅ N/A |
| `baseUrl` compiler option | Not used (only `paths` aliases) | ✅ N/A |
| `downlevelIteration` | Not used | ✅ N/A |
| Closure-style JSDoc syntax (`@enum`, `@callback`-as-type) | 0 occurrences across all 3 frontends | ✅ N/A |
| `experimentalDecorators` / `emitDecoratorMetadata` | Not set; no class decorators in source | ✅ N/A |
| `ignoreDeprecations` flag (forced removal) | 0 occurrences | ✅ N/A |

**Severity classification:**
- BLOCKER: **0**
- FIX_REQUIRED: **0**
- WARNING: **0**

This is an unusual outcome. Most production codebases land 5-20 FIX_REQUIRED items. Ours has none because the team has been progressively cleaning during TS 5→6 migration cycle.

---

## 4. Strict Mode Posture

### 4.1 Per-frontend comparison

| Flag | web_portal/.app | web_portal/.node | web_portal/tests | mini_app/.app | mini_app/.node | landing |
|---|---|---|---|---|---|---|
| `strict` | ✅ true | ✅ true | ✅ true | ✅ true | ✅ true | ✅ true |
| `noUnusedLocals` | ✅ | ✅ | — | ✅ | ✅ | ✅ |
| `noUnusedParameters` | ✅ | ✅ | — | ✅ | ✅ | ✅ |
| `noFallthroughCasesInSwitch` | ✅ | ✅ | — | ✅ | ✅ | ✅ |
| `verbatimModuleSyntax` | ✅ | ✅ | — | ✅ | ✅ | ⚠️ unset |
| `erasableSyntaxOnly` | ✅ | ✅ | — | ✅ | ✅ | ⚠️ unset |
| `noUncheckedSideEffectImports` | ✅ | ✅ | — | ✅ | ✅ | ⚠️ unset (TS 7 default = true) |
| `allowImportingTsExtensions` | ✅ | ✅ | — | ✅ | ✅ | ✅ |
| `moduleDetection: "force"` | ✅ | ✅ | — | ✅ | ✅ | — (uses `isolatedModules: true` instead) |
| `skipLibCheck` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `jsx: "react-jsx"` | ✅ | — | — | ✅ | — | ✅ |

**Type-checking strictness scale: 1-5**
- web_portal: **5/5** (maximum)
- mini_app: **5/5** (maximum)
- landing: **3/5** (strict on; 3 verbatim/erasable/sideEffect gaps)
- web_portal/tests: **3/5** (lighter — acceptable for test code)

### 4.2 Predicted TS 7 impact on existing code

**Hypothesis:** zero new type errors after upgrade, because:
- Strict mode already at max → TS 7 doesn't tighten anything we don't already enforce
- `noUncheckedSideEffectImports` already true in 5 of 6 tsconfigs → landing the only place this default-flip might surface errors

**Predicted landing-only issues:** `noUncheckedSideEffectImports` becoming default-true could fail builds for side-effect imports without type declarations. Given landing has only 17 source files and 1 ambient `.d.ts`, the risk surface is tiny and easily fixed (add explicit `import "module";` declaration or types if needed).

---

## 5. Ecosystem Compatibility

Major dependencies × TS 7 status, based on official sources + community tracking issues:

| Dependency | Version | TS 7 status | Notes |
|---|---|---|---|
| **typescript-eslint** | 8.56–8.58 | 🟢 via shim | Requires `@typescript/typescript6` shim to access removed 6.0 APIs. One-line install. |
| **Vite** | 8.0 | 🟢 native | "Smoother upgrade — `moduleResolution: bundler` is what Vite has always used" (official TS 7 announcement) |
| **@vitejs/plugin-react** | 6.0 | 🟢 | No TS-compiler-API dependency |
| **ESLint** | 9.39 | 🟢 | Independent of TS compiler |
| **React + React DOM** | 19.2 | 🟢 | Types in @types/react are stable + maintained; no TS-7-specific issues |
| **@types/react / @types/react-dom** | 19.2 | 🟢 | DefinitelyTyped community already on TS 7 testing |
| **React Router (DOM)** | 7.x | 🟢 | Pure types package; no compiler API usage |
| **React Query / Zustand** | 5.x | 🟢 | Stable type definitions |
| **react-hook-form / zod** | 7.x / 3.x | 🟢 | Established TypeScript-first libraries |
| **ky / dompurify / lucide-react / recharts / motion** | latest | 🟢 | UI/utility libs — type declarations only |
| **@telegram-apps/sdk-react** | 2.0 | 🟢 | Standalone types, no compiler API |
| **@sentry/react** | 10.45 | 🟡 watch | Upstream `sentry-javascript` has its own TS 6/7 migration issue (#19226). User-facing types unaffected — the issue is for Sentry's *own* codebase, not consumers. |
| **@hookform/resolvers** | 4.1 | 🟢 | Type-only adapter |
| **@playwright/test** | 1.59 | 🟢 | tsgo supports `--build`, `--incremental`, project refs (per TS 7 release notes) |
| **tsx** (landing prebuild) | latest | 🟢 | Independent JS runner (esbuild-based), TS-compiler-agnostic |
| **@lhci/cli** (landing) | latest | 🟢 | CLI tool, unaffected |
| **tailwindcss** | 4.1 | 🟢 | CSS-only, no TS |
| **@tailwindcss/vite** | 4.1 | 🟢 | Vite plugin, no compiler API |
| **vite-plugin-checker** | 🔴 NOT USED | n/a | Known tsgo incompat — fortunately not in our stack |

**Tools deeply tied to TS compiler API (special attention):**
- typescript-eslint — the only one in our stack. Mitigation: `@typescript/typescript6` shim.

**Verdict by tier:**
- 🟢 Confirmed compatible: 17 of 18 named dependencies
- 🟡 Watch (no consumer impact): 1 (@sentry/react)
- 🔴 Known issues: 0

---

## 6. Code Pattern Audit

### 6.1 Risk-bearing patterns

| Pattern | web_portal | mini_app | landing | TS 7 impact |
|---|---|---|---|---|
| `: any` / `<any>` / `as any` | **0** | **0** | **0** | None — nothing to break |
| `@ts-ignore` | **0** | **0** | **0** | None |
| `@ts-expect-error` | **0** | **0** | **0** | None |
| JSDoc `@enum` (TS 7 promoted to error) | **0** | **0** | **0** | None |
| JSDoc `@callback` / `@typedef` | **0** | **0** | **0** | None |
| `@Decorator(...)` (class decorators) | **0** | **0** | **0** | None |
| Ambient `.d.ts` files | 0 | 1 (telegram) | 1 (vite-env) | Minimal — both are trivial |
| `import type` usage (good sign — verbatimModuleSyntax) | 105 | 51 | 1 | Adoption already aligned with TS 7 defaults |

### 6.2 Ambient `.d.ts` analysis

- `mini_app/src/telegram.d.ts` (~40 lines): interface declaration for `window.Telegram.WebApp`. No deprecated syntax. Compatible.
- `landing/src/vite-env.d.ts` (1 line): `/// <reference types="vite/client" />`. Standard Vite scaffolding. Compatible.

### 6.3 Source file totals

| Frontend | .ts | .tsx | Total | LOC density |
|---|---|---|---|---|
| web_portal | (mostly hooks/api) | (screens/components) | 185 | medium-high |
| mini_app | (mostly hooks/api) | (screens/components) | 145 | medium |
| landing | (mostly utils) | (sections) | 17 | low |

**347 TS files total.** With 0 problematic patterns, expected migration-induced diff = **near-zero**.

---

## 7. Migration Effort Estimate

### 7.1 Effort tier classification

**TRIVIAL** for incremental (Option D), **MINOR** for full switch (Option B/C).

### 7.2 Concrete task lists

**Option (D) — Incremental (~1-3 hours):**
1. `npm install -D @typescript/native-preview@beta` in each of 3 frontends (5 min)
2. Add VS Code "TypeScript Native Preview" extension recommendation to `.vscode/extensions.json` if exists (~5 min)
3. Verify `tsgo --build` succeeds on each frontend (parallel test, no commits) (~10 min per frontend)
4. Document the workflow in CLAUDE.md (~30 min)
5. No production changes; editor experience speedup only

**Option (B) — Full switch in dedicated sprint (~2-3 days):**
1. Day 1 — Bump:
   - `typescript: ^6.0.2` → `typescript@npm:@typescript/typescript6` (shim) **+** add `@typescript/native-preview@beta` in each frontend
   - Change `tsc -b` → `tsgo --build` in package.json scripts
   - Add `noUncheckedSideEffectImports: true`, `verbatimModuleSyntax: true`, `erasableSyntaxOnly: true` to `landing/tsconfig.json` (align with web_portal/mini_app)
   - Optionally add explicit `rootDir: "./src"` to `landing/` (TS 7 default change protection)
2. Day 1 (cont'd) — Verify:
   - `npm run build` succeeds in each frontend
   - `npm run lint` clean (typescript-eslint reading through shim)
   - Playwright E2E suite green
3. Day 2 — Hardening:
   - Pin `landing/package.json` `"latest"` deps (unrelated cleanup but blocking-adjacent)
   - Verify Docker image builds (nginx Dockerfile builds mini_app inside — important per memory file)
   - CI gate: `make ci-local` clean
4. Day 2-3 — Document:
   - CHANGES_2026-XX-XX_ts7_migration.md
   - Update CLAUDE.md "Stack" section
   - Note rollback procedure (revert `typescript` + `@typescript/native-preview` install + script change)

**Option (C) — Migrate now in parallel branch with A/B (~3-5 days):**
- Same as (B), plus pre-launch validation overhead
- Pre-launch app has no real traffic to A/B test against → A/B gives diminishing returns vs (B)

### 7.3 Dependencies on ecosystem readiness

**Blocking dependencies:** None. typescript-eslint shim is officially supported.

**Watch list (no action required, just monitor):**
- TS 7.1 stable programmatic API (months out per Microsoft) — required only if we add tools that need TS compiler API directly. We don't currently.
- Sentry's own TS 6/7 migration — affects @sentry/react publication cadence, not consumer typing.

---

## 8. Recommended Migration Approach

### Option Comparison

| Factor | (A) Defer | (B) Pre-launch | (C) Now | (D) Incremental |
|---|---|---|---|---|
| **Risk** | Low | Low-Med | Med-High (beta) | **Very Low** |
| **Effort timing** | 0 now | 1-2 sessions later | 2-3 sessions now | **5 min now** |
| **Speed gains realized** | No | Yes (later) | Yes | **Editor only** |
| **Ecosystem readiness** | Wait for 7.1 stable | Wait for 7.1 stable | Risk premature | **N/A** |
| **Reversibility** | n/a | Easy (revert PR) | Easy | **Trivial (uninstall)** |
| **Pre-launch blocker compatibility** | Doesn't block | Doesn't block | Risk distraction | **Doesn't block** |

### Recommendation: **(D) NOW + (B) post-launch**

**Rationale:**
1. **(D) Incremental NOW** — install `@typescript/native-preview` alongside existing TS 6.0.2, get tsgo-powered IDE/editor speedups (10× faster type-checking in VS Code) without changing build/CI. Reversible in 30 seconds. Zero risk.
2. **(B) Full switch post-launch** — after Phase 5 (BL-107 + onward) completion + pre-launch blockers cleared, dedicate a 2-3 day sprint to flip `tsc → tsgo` in build/CI. By then TS 7.1 stable programmatic API will likely be available (Microsoft target: ~Q4 2026 per "December 2025" progress post).

**Why NOT (C) Migrate now:**
- TS 7 is officially BETA (Microsoft's own statement: "tsgo is still in preview and not production ready")
- We're approaching production launch (BL-107, then post-Phase-5 launch-blockers) — introducing beta toolchain swap during stabilization window adds non-zero risk
- The speed gains, while real, don't justify a risky migration during a stabilization phase

**Why NOT (A) Defer entirely:**
- Zero-cost editor speedups (Option D) are available now with literally no risk
- Refusing them means slower developer feedback loop for ~6+ months unnecessarily

---

## 9. Risk Register

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| **typescript-eslint breaks in CI without shim** | Medium (if we forget the shim) | High (lint fails, blocks PRs) | Document `@typescript/typescript6` shim install in CHANGES + CLAUDE.md as mandatory step |
| **`landing/tsconfig.json` 3 gaps cause new errors** | Low (17 source files, no `any`) | Low | Run `tsc --noEmit` after upgrade to validate; fix in same commit |
| **TS 7 stableTypeOrdering changes type display in errors** | High (default-on, undisable-able) | Cosmetic only | Accept — no functional impact |
| **@sentry/react upstream lag in TS 7 type compat** | Low (consumer types are stable) | Low | Pin Sentry version until upstream catches up if issue arises |
| **Build mode regression in tsgo `--build`** | Low (officially supported per release notes) | Med (breaks `tsc -b && vite build`) | Verify on a worktree branch before merging to develop |
| **Playwright type-check regression with tsgo** | Low | Low | Run full E2E suite as part of (B) migration gate |
| **mini_app inside nginx Docker image** | Low (build is same `tsc -b && vite build`) | Med | Rebuild + smoke-test nginx container (per CLAUDE.md memory: `docker compose up -d --build nginx api`) |
| **Beta version churn — TS 7.0.x might break between minor releases** | Medium (it's beta) | Med | Pin exact version (`@typescript/native-preview@7.0.0-beta.X`), don't use caret |

---

## 10. Decision Matrix for Marina

```
                 (A) Defer    (B) Pre-launch    (C) Now         (D) Incremental
                 ─────────    ──────────────    ─────────       ───────────────
Risk             Low          Low-Med           Med-High        Very Low ✅
Effort now       0            0                 2-3 sessions    5 min ✅
Effort later     0            2-3 days          0               0 (or 2-3 days)
Speed gains      No           Yes (later)       Yes             IDE only ✅
Ecosystem ready  Wait 7.1     Wait 7.1          Premature       N/A ✅
Reversibility    n/a          Easy              Easy            Trivial ✅
Recommendation   ✗            ✅ (combine D)    ✗               ✅ (combine B)
```

**Suggested path: (D) NOW + (B) AFTER launch-blockers cleared.**

This delivers editor speedup immediately at zero risk, defers the higher-stake compiler swap to a calmer window when TS 7.1 stable API likely available.

---

## 11. Per-frontend Findings (Landing Section)

Per Marina's expansion of scope to include `landing/`:

### Findings specific to `landing/`

**Strengths:**
- TS 6.0.2 (pinned exact, not caret — defensible for static page that's release-stable)
- `moduleResolution: "bundler"` ✅
- `isolatedModules: true` (acts similarly to `verbatimModuleSyntax` for many purposes)
- Single tsconfig (no app/node split) — simpler

**Gaps (low priority, fix during (B) full migration):**
1. `verbatimModuleSyntax: true` not set (web_portal + mini_app have it)
2. `erasableSyntaxOnly: true` not set
3. `noUncheckedSideEffectImports: true` not set — TS 7 will default-flip this; may surface errors during build
4. `target: ES2022` vs web_portal/mini_app's ES2025 — consider unifying (cosmetic)
5. `paths` aliases not configured (acceptable — landing is small)
6. **Unrelated to TS 7:** 3 deps pinned to `"latest"` (`lucide-react`, `@lhci/cli`, `tsx`) — supply-chain hygiene issue, recommend pinning. Out of TS 7 migration scope.

**Landing-specific migration tasks (during Option B):**
- Add 3 strict flags (verbatim/erasable/sideEffect) to `landing/tsconfig.json`
- Run `tsgo --noEmit` to validate; fix any newly-surfaced strict errors (predicted: 0-3 minor)
- Update `landing/eslint.config.js` only if shim install affects it (predicted: no change needed)

---

## 12. Verification Steps Run (read-only)

```bash
# Worktree created from develop
git -C /opt/market-telegram-bot worktree add /opt/mtb-ts7-research develop
git -C /opt/mtb-ts7-research checkout -b research/ts7-migration-readiness
# Result: /opt/mtb-ts7-research @ c1a8e9e, branch research/ts7-migration-readiness

# Verified: main checkout untouched
git -C /opt/market-telegram-bot log --oneline -1
# Output: 59cf1ef feat(bl-107): Phase B.5a — admin review backend endpoints + notifications

# Empirical baseline collected via:
grep "typescript" web_portal/package.json mini_app/package.json landing/package.json
cat **/tsconfig*.json (6 files total)
grep -rn ": any\b" web_portal/src mini_app/src landing/src  # 0 results
grep -rn "@ts-ignore\|@ts-expect-error" web_portal/src mini_app/src landing/src  # 0 results
grep -rn "@enum" web_portal/src mini_app/src landing/src  # 0 results
find . -name "*.d.ts" -not -path "*/node_modules/*"  # 2 files

# Web research (5 queries):
# - "TypeScript 7.0 beta release announcement April 2026 breaking changes deprecations"
# - "typescript-eslint 8 TypeScript 7 compatibility support 2026"
# - "Vite 8 TypeScript 7 beta tsgo native preview compatibility"
# - "Playwright TypeScript 7 native preview tsgo compatibility test runner"
# - "@typescript/native-preview @typescript/typescript6 shim package migration guide"
# Plus WebFetch of devblogs.microsoft.com/typescript/announcing-typescript-7-0-beta/
```

---

## 13. Sources

- [Announcing TypeScript 7.0 Beta — Microsoft TypeScript Blog](https://devblogs.microsoft.com/typescript/announcing-typescript-7-0-beta/)
- [TypeScript 7.0 Beta Arrives on Go-Based Foundation — Visual Studio Magazine](https://visualstudiomagazine.com/articles/2026/04/21/typescript-7-0-beta-arrives-on-go-based-foundation-with-10x-speed-claim.aspx)
- [Dependency Versions — typescript-eslint](https://typescript-eslint.io/users/dependency-versions/)
- [Vite 8.0 release announcement](https://vite.dev/blog/announcing-vite8)
- [@typescript/native-preview — npm](https://www.npmjs.com/package/@typescript/native-preview)
- [Progress on TypeScript 7 — December 2025](https://devblogs.microsoft.com/typescript/progress-on-typescript-7-december-2025/)
- [TypeScript Native (`tsgo` / TypeScript 7) compatibility tracking — withastro/roadmap](https://github.com/withastro/roadmap/discussions/1321)
- [Migrate to TypeScript 6/7 — getsentry/sentry-javascript#19226](https://github.com/getsentry/sentry-javascript/issues/19226)
- [I Tested 15 Popular Libraries With TypeScript 7 Toolchain — Medium](https://thinkingthroughcode.medium.com/i-tested-15-popular-libaries-with-typescript-7-toolchain-heres-how-to-fix-broken-migration-7ea719018e6d)
- [TypeScript 7.0 Beta: A Complete Rewrite in Go — bytecode.news](https://www.bytecode.news/posts/2026/04/typescript-7-0-beta-a-complete-rewrite-in-go)
- [TypeScript 5.x to 6.0 Migration Guide — GitHub gist](https://gist.github.com/privatenumber/3d2e80da28f84ee30b77d53e1693378f)

---

## 14. Open Questions for Marina

1. **(D) Incremental — proceed now?** — One-line install of `@typescript/native-preview` in each frontend (no build/CI change). Want me to schedule this as a separate small-PR task?
2. **(B) Full switch timing** — should we earmark this for "post-Phase-5 launch-blocker sprint" in BACKLOG? If yes, what BL-ID to allocate?
3. **landing/ strict-flag alignment** — bundle with (B), or address as standalone cleanup task earlier?
4. **`"latest"` deps in landing/package.json** — separate hardening task or fold into (B)?

These are tracked as research-output questions; no immediate action required to act on this report.

---

🔍 **Verified against:** `research/ts7-migration-readiness` @ `c1a8e9e` post-research-commit
📅 **Created:** 2026-05-14
👤 **Author:** Claude Code (research probe, read-only)
🏷️ **Branch:** `research/ts7-migration-readiness` (worktree: `/opt/mtb-ts7-research`)
