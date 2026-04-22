# Web Portal — RekHarbor

SPA на React 19 + TypeScript 6 + Vite 8 + Tailwind v4, обслуживается через
nginx. Работает против FastAPI-бэкенда (см. `src/api/`).

## Структура

```
web_portal/
├── src/
│   ├── api/           — единственное место с fetch/ky-вызовами
│   ├── hooks/         — React Query-обёртки поверх api/
│   ├── screens/       — страницы приложения (только hook'и, никакого api)
│   ├── components/    — реиспользуемые UI-компоненты
│   ├── shared/ui/     — примитивы DS v2 (Button, Icon, Card, ...)
│   ├── lib/types/     — руч­ные TS-типы (постепенно заменяются на
│                         генерируемые из OpenAPI)
│   └── App.tsx        — router + layout shell
├── tests/             — Playwright E2E (см. tests/README.md)
└── vite.config.ts
```

## API Conventions (FIX_PLAN_06 §6.7)

**Единственный путь вызова бэкенда: `screen → hook → api-module`.**

Запрещено (проверяется в CI):
- `import { api }` внутри `src/screens/**`, `src/components/**`,
  `src/hooks/**` — вызывать `api.*` можно только из `src/api/<domain>.ts`.
- Использовать устаревшие поля и phantom-пути (`reject_reason`,
  `acts/?placement_request_id`, `reviews/placement/`,
  `placements/${id}/start`, `reputation/history`, raw
  `channels/${id}`). Список в `scripts/check_forbidden_patterns.sh`.

Два уровня защиты:
1. **ESLint (`eslint.config.js`)** — `no-restricted-imports` блокирует
   прямой `import { api }` в screens/components/hooks.
2. **`scripts/check_forbidden_patterns.sh`** — bash-grep backstop по
   7 паттернам. Запускается в `make ci` и в
   `.github/workflows/contract-check.yml`.

## Как добавить endpoint

1. **Бэкенд.** Pydantic-схема ответа в `src/api/schemas/<domain>.py`
   (или прямо в роутере для одноразовых моделей). Если добавляется
   одна из 8 контролируемых моделей (User, Placement, Payout,
   Contract, Dispute, LegalProfile, Channel, UserAdmin) — после
   изменения запустить `UPDATE_SNAPSHOTS=1 poetry run pytest
   tests/unit/test_contract_schemas.py` и закоммитить обновлённый
   snapshot в ту же PR.
2. **API-модуль.** В `web_portal/src/api/<domain>.ts` добавить
   функцию-обёртку:
   ```ts
   export async function getThing(id: number): Promise<ThingResponse> {
     return api.get(`things/${id}`).json<ThingResponse>()
   }
   ```
3. **Hook.** В `web_portal/src/hooks/use<Domain>.ts` — React Query:
   ```ts
   export function useThing(id: number) {
     return useQuery({ queryKey: ['thing', id], queryFn: () => getThing(id) })
   }
   ```
4. **Экран.** В `web_portal/src/screens/<path>/<Screen>.tsx` — только
   hook:
   ```tsx
   const { data, isLoading, error } = useThing(id)
   ```

Любая попытка срезать путь и вызвать `api.get(...)` прямо из screen'а
или hook'а — fail в `eslint` и `make check-forbidden`.

## Разработка

```bash
# Установка зависимостей
npm ci

# Dev-сервер на 5173, проксирует /api в локальный FastAPI
npm run dev

# Production-сборка (tsc -b + vite build)
npm run build

# Lint + typecheck
npm run lint
npx tsc --noEmit -p tsconfig.json

# E2E-тесты в Docker-стеке
make -C .. test-e2e
```

## CI (FIX_PLAN_06 §6.3)

- `.github/workflows/frontend.yml` — `tsc --noEmit` на каждый PR для
  `web_portal`, `mini_app`, `landing`.
- `.github/workflows/contract-check.yml` — grep-guards + contract-drift
  snapshots + `tests/unit/api/`.
- Polyglot E2E — локально через `make test-e2e` (Playwright в
  docker-compose.test.yml), см. `tests/README.md`.

## Стек (кратко)

- React 19.2.4
- TypeScript 6.0.2
- Vite 8
- Tailwind v4 (@theme tokens в `src/styles/globals.css`)
- React Router 7
- React Query 5
- ky (HTTP-клиент) + zod (валидация ответов)
- Playwright (E2E)
- ESLint (flat config)
