# Стартовый промт для следующей сессии

Скопируй блок ниже в новую Claude Code сессию (после `/clear`).

---

```text
Продолжаем работу по /opt/market-telegram-bot/reports/20260419_diagnostics/.

Актуальное состояние (после сессии 2026-04-19):

- main = bc4f19b (S-43 + S-44 Stage 3 + GitHub integration + smoke report)
- develop = 57e34f9
- feat/s-44-missing-integration = e5e17e0 (оставлена, не удаляем)
- Последние merge-commits: 57e34f9 develop, bc4f19b main — оба запушены.

Что уже сделано (S-44 Stage 3, см.
reports/docs-architect/discovery/CHANGES_2026-04-19_s44-missing-integration.md):
§3.1 TopUp polling, §3.2 AdminPayouts в сайдбаре, §3.4 accept-rules badge,
§3.7 Evidence в OpenDispute, §3.8a admin credits, §3.8b KUDiR auth fix,
Stage 2 leftovers (ContractData.contract_status, phantom Payout re-exports).
Отложено в next-sprint backlog: §§ 3.3 (CampaignVideo uploads), 3.5 (PRO
analytics), 3.6 (channel preview), прочие admin-экраны §3.8.

Критические находки из SMOKE_TEST_2026-04-19_portal-prod.md (prod
https://portal.rekharbor.ru) — НЕ ЗАКРЫТЫ:

P0 блокеры:
  - A1: GET /api/channels/available?category=... → HTTP 422 (int_parsing).
    Бэк парсит слово «available» как channel_id:int → wizard «Создать
    кампанию» сломан end-to-end. Считалось, что S-42 §1 это пофиксил —
    на проде проблема живёт.
  - D1: фронт шлёт passport_issued_at, бэк ждёт passport_issue_date
    (S-43 §2.5 не доехал). Паспорт не сохраняется → legal profile блок.
  - F1 admin: GET /api/disputes/admin/disputes?status=open&limit=20 → 500
    Internal Server Error. Админ не может видеть/решать споры, а 1 открытый
    уже висит.

P1:
  - E1/E2/E3: AdminPayouts chunk не попал в prod-bundle (роут /admin/payouts
    → 404 на проде несмотря на S-42 §1.6 и S-44 §3.2). Нужна
    диагностика build-pipeline.
  - A7: роут /profile/reputation → 404 в SPA — UI для истории репутации
    не зарегистрирован, хотя бэк готов.

P2 drift leftovers (S-43 должен был их убрать):
  - page_size в useCampaignQueries (1× — должно быть limit/offset).
  - owner_comment ещё в 3 чанках (useDisputeQueries, DisputeDetail,
    MyDisputes) — должно быть owner_explanation.
  - gross_amount не найден ни в одном фронтовом чанке (B3 payouts).
  - has_passport_data не читается фронтом (метка «Паспорт добавлен» не
    рендерится).

План на эту сессию — разбить в 2 этапа:

ЭТАП А (hotfix, ~3–4 часа) — ветка `fix/s-48-prod-smoke-blockers` от main:
  1. A1: диагностировать, почему /api/channels/available возвращает 422.
     Проверить — существует ли endpoint вообще; если нет, добавить; если
     есть, понять почему роутинг падает на int_parsing. Файлы:
     src/api/routers/channels.py, web_portal/src/api/channels.ts,
     web_portal/src/screens/advertiser/campaign/CampaignChannels.tsx.
  2. D1: добавить passport_issue_date в LegalProfileSetup, убрать старое
     passport_issued_at. Проверить backend принимает новое имя.
     Файл: web_portal/src/screens/common/LegalProfileSetup.tsx.
  3. F1: разобрать 500 на /api/disputes/admin/disputes. Логи смотреть
     через `docker compose logs api --tail=200`. Починить серверный краш.
  4. E1 prod-bundle: проверить, вошёл ли AdminPayouts.tsx в prod build
     (grep AdminPayouts в dist/ через `docker compose exec nginx ls
     /usr/share/nginx/html/assets/`). Если chunk пропал — проверить
     lazy-import и App.tsx.
  5. A7: добавить маршрут /profile/reputation + простой screen рядом с
     существующими хуками useReputationQueries.
  6. S-43 drift leftovers — page_size→limit/offset, owner_comment→
     owner_explanation, покрыть gross_amount / has_passport_data.

  CHANGES_2026-04-19_s48-prod-smoke-blockers.md + CHANGELOG [Unreleased].
  Git-flow: fix/s-48 → develop → main (--no-ff, сохранить ветку).

ЭТАП B (если успеваем) — стартовать Stage 7 (UI redesign DS v2):
  План уже подготовлен в reports/20260419_diagnostics/FIX_PLAN_07_ui_
  redesign_ds_v2.md (не в git — он под .gitignore reports/*). Начать с
  §§ 7.0–7.2: перенос handoff-бандла в reports/design/test-avatars-
  handoff-2026-04-19/ (под git, whitelist), Design tokens v2 в
  @theme, Icon-компонент из handoff-icons.jsx.
  Ветка: feat/s-47-ui-redesign-ds-v2 от main.
  Handoff в корне: /opt/market-telegram-bot/Test Avatars-handoff.zip
  (сейчас untracked).

Ключевые напоминалки:
  - После backend/frontend правок: docker compose up -d --build nginx api
  - make lint (ruff) baseline — 3 pre-existing ошибки, не добавлять новых
  - web_portal: cd web_portal && npx tsc --noEmit -p tsconfig.app.json
  - Semantic commits per-группа, никогда git add .
  - Git flow CLAUDE.md: feature → develop (--no-ff) → main (--no-ff),
    ветку сохранять. На любой merge-конфликт — STOP и доложить.
  - Ветки feat/s-42, feat/s-43, feat/s-44 — сохранены, не удалять.
  - Полный fix-план: reports/20260419_diagnostics/FIX_PLAN_00_index.md
    (86–118 часов, 7 этапов). Готовые: 1, 2, 3. Осталось: 4, 5, 6, 7.

Стартовая команда:
git checkout main && git pull origin main && git checkout -b fix/s-48-prod-smoke-blockers
```

---

## Что в этом промте заложено

1. **Снимок состояния**: три ветки, последние commit-хеши, что уже смержено.
2. **Backlog from smoke**: дословные симптомы P0/P1/P2, с путями к файлам.
3. **Две опции работы**: hotfix (fix/s-48) или переход на UI redesign (feat/s-47).
4. **Git-flow напоминание**: ветки сохраняются, --no-ff, конфликты → STOP.
5. **Проверки качества**: ruff baseline, tsc, docker rebuild.

## Почему именно эта структура

- S-44 закрыт и в main. Переходить к Stage 4 backend cleanup **нельзя** пока
  P0-блокеры из smoke живут на проде.
- GitHub integration (`77f50e9`) теперь на main — следующая сессия может её
  использовать для автоматического создания issue по каждому блокеру.
- Stage 7 (UI redesign) — P1, его можно начать параллельно с hotfix-ом, но
  только ПОСЛЕ того как S-48 фиксы стабилизируются на develop (иначе конфликты).
