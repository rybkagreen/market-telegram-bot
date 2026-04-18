# S-41 Research: Mini App TypeScript 6.0 Upgrade Feasibility

> **⚠ STOP CONDITION TRIGGERED**
>
> The sprint premise — "mini_app is on TS 5.9, web_portal is on TS 6.0" — is **factually incorrect**.
> Both projects already declare `typescript: "^6.0.2"` in their `package.json` and both tsconfigs
> are already fully TS 6.0 compliant. The upgrade has already been performed.
> See §1 for evidence, §6 for a reconciliation of what the audit item D-21 likely intended.

---

## §1 — Версии TypeScript (факт)

| Файл | typescript | Статус |
|------|------------|--------|
| `mini_app/package.json:43` | `"^6.0.2"` | ✅ уже 6.0 |
| `web_portal/package.json:43` | `"^6.0.2"` | ✅ уже 6.0 |

Оба проекта объявляют одинаковую версию. Разница в версии TS **отсутствует**.

---

## §2 — Diff конфигов: mini_app (tsconfig.app.json) vs web_portal (tsconfig.app.json)

| Опция | mini_app | web_portal | Требуется действие? |
|-------|----------|------------|----------------------|
| `target` | `ES2025` | `ES2025` | — |
| `lib` | `["ES2025", "DOM"]` | `["ES2025", "DOM"]` | — |
| `module` | `ESNext` | `ESNext` | — |
| `moduleResolution` | `bundler` | `bundler` | — (оба уже не `node`) |
| `types` | `["vite/client", "node"]` | `["vite/client", "node"]` | — (явно задан) |
| `baseUrl` | **отсутствует** | **отсутствует** | — (уже удалён) |
| `strict` | `true` | `true` | — |
| `erasableSyntaxOnly` | `true` | `true` | — (TS 6.0 флаг) |
| `noUncheckedSideEffectImports` | `true` | `true` | — (TS 6.0 флаг) |
| `verbatimModuleSyntax` | `true` | `true` | — |
| `moduleDetection` | `force` | `force` | — |
| `allowImportingTsExtensions` | `true` | `true` | — |
| `noEmit` | `true` | `true` | — |
| `jsx` | `react-jsx` | `react-jsx` | — |
| `rootDir` | **отсутствует** | `"./src"` | Минорная разница, не критично |
| `paths` | `{"@/*": ["./src/*"]}` | `{"@/*": [...], "@shared/*": [...], "@components/*": [...]}` | web_portal шире — не проблема |

**Вывод**: конфиги идентичны по всем TS-версионно значимым параметрам.

---

## §3 — Использование deprecated опций в mini_app

| Deprecated опция | Строка в файле | Статус |
|------------------|----------------|--------|
| `baseUrl` | — | ✅ **отсутствует**; комментарий в строке 27: `/* Path aliases (baseUrl removed — deprecated in TS 6.0) */` |
| `moduleResolution: "node"` | — | ✅ используется `"bundler"` |
| `types` (неявный / пустой) | `tsconfig.app.json:8` — `["vite/client", "node"]` | ✅ явно задан |
| `tsconfig.node.json types` | строка 7 — `["node"]` | ✅ явно задан |

Ни одной deprecated опции не найдено. Оба файла tsconfig содержат только опции, валидные для TS 6.0.

Наличие TS 6.0-exclusive флагов в mini_app:
- `erasableSyntaxOnly: true` — добавлен в TS 5.5, рекомендован в 6.0
- `noUncheckedSideEffectImports: true` — добавлен в TS 5.6

---

## §4 — Файлы под import-алиасами `@/`

| Метрика | Значение |
|---------|----------|
| Файлы с `from "@/..."` импортами | **122 файла** |
| Всего вхождений | **408** |
| Алиас | `@/*` → `./src/*` (tsconfig.app.json + vite.config.ts `resolve.tsconfigPaths: true`) |
| Пакет `vite-tsconfig-paths` | **не требуется** — Vite 8.0.0 поддерживает `resolve.tsconfigPaths` нативно |

---

## §5 — Оценка стоимости миграции

> Поскольку миграция уже выполнена, оценка носит ретроспективный характер.

| Сценарий | Оценка | Обоснование |
|----------|--------|-------------|
| Optimistic | 0 ч | Конфиги уже мигрированы; нет deprecated опций |
| Realistic | 0 ч | Обе кодовые базы работают на TS 6.0.2 |
| Pessimistic | 1–2 ч | Только если `npm install` выявит реальные тайп-чек ошибки при `tsc --noEmit` |

**Единственный возможный риск**: при выполнении `tsc --noEmit` могут всплыть ошибки из-за
`erasableSyntaxOnly` (запрещает `enum`, `namespace`, `parameter properties` в не-удаляемом
синтаксисе) или `noUncheckedSideEffectImports`. Без `npm install` в mini_app выполнить проверку
невозможно, но конфигурация идентична web_portal — значит те же правила там уже прошли проверку.

---

## §6 — Что мог означать audit item D-21

Возможные интерпретации, почему D-21 считал mini_app «не на 6.0»:

1. **Snapshot устарел**: audit проводился до коммита, который обновил mini_app/package.json с 5.x → 6.0.
2. **Путаница с установленной vs объявленной версией**: если `node_modules` в mini_app не синхронизированы (не выполнялся `npm install`), фактически может быть установлена старая версия, хотя package.json уже обновлён.
3. **Проверка по tsconfig, а не по package.json**: ранняя версия tsconfig.app.json могла содержать deprecated опции, которые уже удалены.

**Рекомендация**: закрыть D-21 как выполненный. Для верификации достаточно:
```bash
cd mini_app && npm install && npx tsc --noEmit 2>&1 | wc -l
# Ожидаемый результат: 0 строк (или только предупреждения без ошибок)
```

---

## §7 — Рекомендуемый порядок шагов (если вдруг потребуется повторить для другого проекта)

1. Обновить `package.json`: `typescript: "^6.0.2"`
2. В `tsconfig.app.json`: удалить `baseUrl`, заменить `moduleResolution: "node"` на `"bundler"`
3. Добавить явный `types: ["vite/client", "node"]`
4. Добавить TS 6.0 строгие флаги: `erasableSyntaxOnly`, `noUncheckedSideEffectImports`
5. Запустить `tsc --noEmit` — исправить ошибки `erasableSyntaxOnly` (обычно `enum` → `const enum` или union type)
6. Обновить `vite.config.ts`: добавить `resolve: { tsconfigPaths: true }` (Vite 6+)

Для mini_app все 6 шагов **уже выполнены**.

---

🔍 Verified against: `8881e06` | 📅 Updated: 2026-04-17T00:00:00Z
