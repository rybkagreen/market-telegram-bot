# lint-fix — Полный цикл проверки качества кода

Запускает ruff check с автофиксом, форматирование, mypy и bandit.
Цель: 0 ошибок перед коммитом.

```bash
cd /opt/market-telegram-bot && \
ruff check src/ --fix && \
ruff format src/ && \
mypy src/ --ignore-missing-imports && \
bandit -r src/ -ll && \
echo "✅ All checks passed"
```

### Опции
- `--fast` — только ruff check + format (пропускает mypy/bandit)
- `--tests` — добавляет `pytest tests/ -v` в конец
- `--coverage` — добавляет `--cov=src --cov-report=term-missing`

### Примеры использования
```
/lint-fix                          # полный цикл
/lint-fix --fast                   # быстрый lint + format
/lint-fix --tests                  # lint + тесты
/lint-fix --tests --coverage       # lint + тесты + coverage
```
