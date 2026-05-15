# CHANGES 2026-05-14 — BL-107 Phase B.9 Phase B (component tests)

## Context

Phase B.9 Phase A bootstrapped vitest + RTL infrastructure in both
frontends. Phase B consumes that infrastructure to add the missing
component tests for 3 BL-107 screens shipped in Phase B.5b:

- web_portal: `AdminChannelVerificationsList`, `AdminChannelVerificationDetail`
- mini_app: `OwnSubmitRegistryEvidence`

**Scope envelope:** narrow test addition + 2 infra-tuning carve-outs
discovered empirically (auto-cleanup + ambient .d.ts inclusion). No
component code touched, no API changes, no migrations.

Built atop Phase B.9.A (`6356f4c`).

## Empirical decisions (versus PROMPT 42 assumptions)

1. **Mock at api-module level**, не fetch-level — using
   `vi.mock('@/api/admin_channel_verifications', () => ({...}))` with
   `vi.importActual` to preserve types, then overriding specific functions
   with `vi.fn()`. Reasons:
   - Component code path remains realistic (real hooks, real QueryClient,
     real React Query lifecycle)
   - Test ergonomics: `vi.mocked(api.fn).mockResolvedValue(...)` >
     hand-rolled fetch stubs
   - Avoids msw dep (excluded by prompt)

2. **`afterEach(cleanup)` added to setup.ts** (Phase A carve-out fix).
   `@testing-library/react`'s auto-cleanup hooks into the global
   `afterEach`, which only exists when `globals: true`. Phase A chose
   `globals: false` for ESLint compatibility → auto-cleanup was silent
   no-op → second test in a file saw the first test's leftover DOM →
   `Found multiple elements` failures. Fix: explicitly call `cleanup()`
   in our `afterEach` registered via `vitest`'s exported `afterEach`.

3. **`src/**/*.d.ts` added to `tsconfig.test.json` include** (Phase A
   carve-out fix). With `moduleDetection: "force"`, ambient declaration
   files (e.g. `mini_app/src/telegram.d.ts` declaring `interface Window`
   augmentation) become module-scoped unless explicitly included or
   marked with `declare global { ... }`. `tsconfig.test.json` only
   included test files originally → test compilation lost the global
   `Window.Telegram` augmentation → `tsc -b` broke. Fix:
   include `src/**/*.d.ts` so ambient declarations propagate to the
   test compilation unit.

4. **`tsconfig.app.json` exclude — replaced brace expansion** (Phase A
   carve-out fix). Original `src/**/*.test.{ts,tsx}` doesn't work —
   TypeScript glob support does NOT include brace expansion. Replaced
   with explicit `.test.ts`, `.test.tsx`, `.spec.ts`, `.spec.tsx` entries.
   Symptom that exposed the bug: tsc-checked test files saw
   `noUnusedLocals` and `jest-dom Assertion` type errors.

5. **`renderWithProviders` test helper** in `src/test/utils.tsx` for each
   frontend — wraps `QueryClientProvider` (fresh client per test, retries
   off, gcTime/staleTime Infinity) + `MemoryRouter` with configurable
   `initialEntries`. Supports passing custom `QueryClient` for advanced
   cases.

6. **`useHaptic` mocked in mini_app tests** — original hook chains through
   `useTelegram` → `window.Telegram.WebApp.HapticFeedback`. Tests run in
   jsdom без Telegram WebApp object. Mock returns no-op functions per
   method. Mock at the **higher** level (useHaptic) rather than
   useTelegram, so other useTelegram consumers aren't accidentally
   stubbed.

7. **`within(panel)` scoping for ambiguous accessible names** —
   `AdminChannelVerificationDetail` renders Verify/Reject toggle buttons
   AND in-form submit buttons with the same accessible name ("Подтвердить"
   / "Отклонить"). Standard `screen.getByRole('button', { name: ... })`
   matches both. Scoping by panel container (`within(formPanel)`)
   disambiguates без adding test-only props к component code.

## Files added

### web_portal (3 files)

| File | Tests | Coverage |
|---|---|---|
| `src/test/utils.tsx` | — | `renderWithProviders` helper, `createTestQueryClient` |
| `src/screens/admin/AdminChannelVerificationsList.test.tsx` | 3 | render-with-items / empty-state / row-click-navigation |
| `src/screens/admin/AdminChannelVerificationDetail.test.tsx` | 3 | render-pending-channel / reject-validation-blocks-API / verify-submits-navigates |

### mini_app (2 files)

| File | Tests | Coverage |
|---|---|---|
| `src/test/utils.tsx` | — | same `renderWithProviders` (per-frontend copy — keeps frontends independent) |
| `src/screens/owner/OwnSubmitRegistryEvidence.test.tsx` | 3 | render-fields / submit-trimmed-payload-navigates / empty-application-number-blocks |

## Files modified (Phase A carve-out fixes)

### web_portal

- `src/test/setup.ts` — added `afterEach(cleanup)` (decision #2)
- `tsconfig.app.json` — replaced brace-expansion exclude with explicit
  per-extension patterns (decision #4)
- `tsconfig.test.json` — added `src/**/*.d.ts` to include (decision #3)

### mini_app

Same set of modifications.

## Test count

| Frontend | Smoke (Phase A) | Component (Phase B) | Total |
|---|---|---|---|
| web_portal | 1 | 6 | 7 |
| mini_app | 1 | 3 | 4 |
| **Total** | **2** | **9** | **11** |

Per Phase B.9 prompt: "≥3 tests per component" × 3 components = ≥9. Met.

## Verification gates

| Gate | web_portal | mini_app |
|---|---|---|
| `npm run test:run` | ✅ 7 passed | ✅ 4 passed |
| `npm run build` (tsc -b + vite build) | ✅ built | ✅ built |
| `npx eslint <new files>` | ✅ clean | ✅ clean |

## Forced scope

Three Phase A carve-out fixes (decisions #2, #3, #4) that surfaced during
Phase B test execution. Marina's prompt allows "expand within sub-block
scope" per Principle 1 — these are test-infra fixes co-located with the
test files that triggered them. Documented above so a future maintainer
sees the cause-effect chain instead of treating these as orthogonal
changes.

## Deferred to production launch

None.

## Next sub-block

Phase C — Playwright BL-002 test.fixme unblock (auto-continue per prompt).

🔍 Verified against: `6356f4c` (Phase B.9.A HEAD) | 📅 Updated: 2026-05-14T21:01:00Z
