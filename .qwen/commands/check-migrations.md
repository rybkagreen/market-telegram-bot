# check-migrations — Проверка состояния Alembic миграций

Сравнивает текущее состояние БД с head миграций.
Используется перед деплоем и после генерации новых миграций.

```bash
cd /opt/market-telegram-bot && \
alembic current && \
echo "---" && \
alembic heads && \
echo "---" &&
alembic check
```

### Опции
- `--upgrade` — показать SQL для `alembic upgrade head --sql`
- `--downgrade N` — показать SQL для отката на N ревизий
- `--history` — показать полную историю миграций

### Примеры использования
```
/check-migrations                    # current + heads + check
/check-migrations --upgrade          # показать SQL upgrade
/check-migrations --downgrade 1      # показать SQL отката
/check-migrations --history          # полная история
```

### Интерпретация результатов
| Вывод | Значение |
|-------|----------|
| `(head)` | Все миграции применены |
| `<revision_id>` | Есть неприменённые миграции |
| `alembic check` вернул ошибку | Конфликт в моделях и миграциях |
