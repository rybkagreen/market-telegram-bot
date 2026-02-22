# Локальные проверки кода (вместо CI)

> **Важно:** GitHub Actions CI отключен из-за блокировки платежного аккаунта. Все проверки выполняются локально через pre-commit хуки.

---

## 📋 Быстрый старт

### 1. Установка pre-commit хуков

```bash
# Один раз после клонирования репозитория
make pre-commit-install
```

### 2. Запуск всех проверок перед коммитом

```bash
# Полная проверка (lint + format + typecheck + tests)
make check
```

Или через pre-commit напрямую:

```bash
pre-commit run --all-files
```

---

## 🔧 Доступные команды

| Команда | Описание |
|---|---|
| `make pre-commit-install` | Установить pre-commit хуки (автоматическая проверка при `git commit`) |
| `make pre-commit-run` | Запустить pre-commit хуки на всех файлах |
| `make check` | Полная проверка: ruff + format + mypy + pytest |
| `make lint` | Проверка ruff (только ошибки) |
| `make format` | Проверка форматирования (ruff format --check) |
| `make typecheck` | Проверка типов (mypy) |
| `make test` | Запуск тестов (pytest) |

---

## 🎯 Как это работает

### Pre-commit хуки (автоматически при `git commit`)

При каждом коммите выполняются:

1. **ruff** — проверка кода и авто-исправление ошибок
2. **ruff-format** — форматирование кода
3. **mypy** — проверка типов (только `src/`, исключая тесты)
4. **pre-commit-hooks** — проверка YAML, концов файлов, пробелов
5. **detect-secrets** — поиск случайно закоммиченных секретов
6. **pytest** — запуск всех тестов

Если хотя бы одна проверка не прошла — коммит отклоняется.

### Ручной запуск (перед push)

Рекомендуется запускать полную проверку перед отправкой кода:

```bash
make check
```

Это выполнит все проверки из CI:
- ✅ `ruff check src/ tests/`
- ✅ `ruff format --check src/ tests/`
- ✅ `mypy src/`
- ✅ `pytest tests/ --tb=short -v`

---

## ⚠️ Если проверки не проходят

### Ruff ошибки

```bash
# Автоматически исправить что можно
make lint-fix

# Или вручную
poetry run ruff check src/ tests/ --fix
```

### Mypy ошибки

Проверьте аннотации типов в файле, на который указывает ошибка.

### Pytest упал

Запустите тесты с подробным выводом:

```bash
poetry run pytest tests/ -v
```

---

## 📝 Workflow для разработки

```bash
# 1. Создать фичу-ветку
git checkout develop && git pull origin develop
git checkout developer/<your-name> && git merge develop
git checkout -b feature/<task-name>

# 2. Внести изменения, закоммитить (pre-commit проверит автоматически)
git add .
git commit -m "feat(scope): description"

# 3. Перед push запустить полную проверку
make check

# 4. Запушить и создать PR
git push origin feature/<task-name>
```

---

## 🚀 Для продвинутых

### Пропустить pre-commit (только для экстренных случаев)

```bash
git commit --no-verify -m "hotfix: ..."
```

### Запустить только определенные хуки

```bash
# Только линтер
pre-commit run ruff --all-files

# Только тесты
pre-commit run pytest --all-files
```

### Обновить зависимости pre-commit

```bash
pre-commit autoupdate
```

---

## 📞 Проблемы?

Если pre-commit хуки не работают:

1. Убедитесь, что Poetry установлен: `poetry --version`
2. Переустановите хуки: `pre-commit uninstall && pre-commit install`
3. Проверьте, что все зависимости установлены: `make install`
