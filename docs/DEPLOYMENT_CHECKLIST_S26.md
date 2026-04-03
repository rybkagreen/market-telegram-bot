# Deployment Checklist — Sprint S-26 (ООО УСН 15%)

> **Дата:** 2026-04-03
> **Цель:** Деплой всех бухгалтерских и налоговых изменений на production (Timeweb)

---

## 1. Pre-Deploy Verification

- [ ] `.env` файл существует и содержит все необходимые переменные:
  - [ ] `DATABASE_URL` (postgresql+asyncpg://...)
  - [ ] `DATABASE_SYNC_URL` (postgresql://...)
  - [ ] `REDIS_URL`, `CELERY_BROKER_URL`
  - [ ] `BOT_TOKEN`, `BOT_USERNAME`
  - [ ] `ADMIN_IDS`
  - [ ] `FIELD_ENCRYPTION_KEY` (для PII шифрования)
  - [ ] `YOOKASSA_SHOP_ID`, `YOOKASSA_SECRET_KEY`
  - [ ] `SENTRY_DSN` (GlitchTip)

- [ ] Все контейнеры запущены и здоровы:
  ```bash
  cd /opt/market-telegram-bot
  docker compose ps
  ```
  Ожидаемый статус: `healthy` для postgres, redis; `running` для всех остальных.

- [ ] Текущая миграция HEAD (до деплоя):
  ```bash
  docker compose exec api poetry run alembic current
  ```
  Ожидается: `s26d002_storno_expense (head)`

- [ ] Статический анализ локально:
  ```bash
  poetry run ruff check src/ --fix && poetry run ruff format src/ && poetry run mypy src/ --ignore-missing-imports
  ```
  Ожидается: `All checks passed!` и `Success: no issues found`

---

## 2. Backup

- [ ] Создать backup базы данных:
  ```bash
  mkdir -p /opt/backups
  docker compose exec -T postgres pg_dump -U market_bot market_bot_db > /opt/backups/db_backup_pre_deploy.sql
  ls -lh /opt/backups/db_backup_pre_deploy.sql
  ```

- [ ] Проверить целостность backup:
  ```bash
  head -5 /opt/backups/db_backup_pre_deploy.sql
  tail -5 /opt/backups/db_backup_pre_deploy.sql
  ```

---

## 3. Deploy

- [ ] Запустить deploy-скрипт:
  ```bash
  cd /opt/market-telegram-bot
  ./scripts/deploy/production_deploy.sh
  ```

- [ ] Проверить лог деплоя:
  ```bash
  tail -50 deploy_$(date +%Y%m%d).log
  ```

---

## 4. Post-Deploy Verification

- [ ] Миграция применена:
  ```bash
  docker compose exec api poetry run alembic current
  ```
  Ожидается: `s26e001_add_document_links (head)`

- [ ] Health check (via docker exec — API port not exposed to host):
  ```bash
  docker exec market_bot_api curl -sf http://localhost:8001/health | python3 -m json.tool
  ```
  Ожидается: `{"status": "healthy", "environment": "production"}`

- [ ] Проверить новые таблицы/колонки в БД:
  ```bash
  docker compose exec postgres psql -U market_bot -d market_bot_db -c "
    SELECT table_name FROM information_schema.tables
    WHERE table_schema='public' AND table_name IN ('acts','invoices','kudir_records','platform_quarterly_revenues','transactions')
    ORDER BY table_name;
  "
  ```

- [ ] Проверить Celery workers:
  ```bash
  docker compose exec worker_critical celery -A src.tasks.celery_app inspect ping
  docker compose exec worker_background celery -A src.tasks.celery_app inspect ping
  docker compose exec celery_beat celery -A src.tasks.celery_app inspect ping
  ```

- [ ] Проверить Flower (мониторинг):
  ```bash
  curl -sf http://localhost:5555/dashboard || echo "Flower not accessible"
  ```

---

## 5. Functional Tests

- [ ] **Налоговая сводка** (ООО УСН 15%):
  ```bash
  # Через Mini App: Admin → Налоги → выбрать квартал → проверить tax_due
  # Или напрямую (API port not exposed — use docker exec or nginx proxy):
  docker exec market_bot_api curl -s "http://localhost:8001/api/admin/tax/summary?year=2026&quarter=1" \
    -H "Authorization: Bearer <admin_token>" | python3 -m json.tool
  ```

- [ ] **KUDiR экспорт CSV**:
  ```bash
  docker exec market_bot_api curl -s "http://localhost:8001/api/admin/tax/kudir/2026/1/csv" \
    -H "Authorization: Bearer <admin_token>" | head -10
  ```

- [ ] **KUDiR экспорт PDF**:
  ```bash
  docker exec market_bot_api curl -s "http://localhost:8001/api/admin/tax/kudir/2026/1/pdf" \
    -H "Authorization: Bearer <admin_token>" -o /tmp/kudir_test.pdf
  file /tmp/kudir_test.pdf
  ```

- [ ] **Сторнирование** (record_storno):
  - Найти любую транзакцию topup в БД
  - Вызвать TaxAggregationService.record_storno(session, txn_id, "test")
  - Проверить: is_reversed=True, квартальные показатели уменьшились

---

## 6. Monitoring

- [ ] Проверить логи на ошибки:
  ```bash
  docker compose logs --tail=100 api | grep -i error
  docker compose logs --tail=100 worker_critical | grep -i error
  ```

- [ ] Проверить GlitchTip (ошибки приложения):
  - Открыть http://localhost:8090
  - Убедиться, что нет новых критических ошибок

- [ ] Проверить Celery Flower:
  - Открыть http://localhost:5555
  - Все workers: active, no failed tasks

---

## 7. Rollback Plan (при необходимости)

1. **Остановить все сервисы:**
   ```bash
   docker compose down
   ```

2. **Восстановить БД из backup:**
   ```bash
   docker compose up -d postgres
   sleep 10
   docker compose exec -T postgres psql -U market_bot -d market_bot_db < /opt/backups/db_backup_pre_deploy.sql
   ```

3. **Откатить миграцию:**
   ```bash
   docker compose up -d api
   docker compose exec api poetry run alembic downgrade -1
   ```

4. **Перезапустить все сервисы:**
   ```bash
   docker compose restart
   ```

5. **Проверить health:**
   ```bash
   docker exec market_bot_api curl -sf http://localhost:8001/health
   ```

---

## 8. Sign-Off

- [ ] Все пункты 1-7 выполнены без ошибок
- [ ] Backup создан и проверен
- [ ] Миграция `s26e001_add_document_links` применена
- [ ] Health check проходит
- [ ] Налоговая сводка корректно рассчитывает УСН 15%
- [ ] KUDiR экспорт (PDF/CSV) работает
- [ ] Мониторинг (Flower, GlitchTip) в норме

**Деплой выполнен:** ____________ (дата/время)
**Выполнил:** ____________
**Подтвердил:** ____________
