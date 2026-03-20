# Code Review — Извлечённые уроки

## Критические ошибки первоначального анализа

### 1. Async/Await — 142 ложных срабатывания

**Проблема:** AST-анализ флагил все вызовы `.scalar()`, `.scalar_one()`, `.scalars().all()` как "missing await"

**Причина:** Не учитывался контекст SQLAlchemy 2.0 async API:
```python
# ПРАВИЛЬНЫЙ паттерн — НЕ требует await для Result методов
result = await session.execute(stmt)  # ← await ЗДЕСЬ
data = result.scalar_one()            # ← синхронный метод, await НЕ нужен
```

**Урок:** 
- `session.execute()` → async, требует await ✓
- `Result.scalar/scalar_one/scalar_one_or_none()` → синхронные ✓
- `Result.scalars()` → синхронный, возвращает ScalarResult ✓
- `ScalarResult.all()` → синхронный ✓

**Как надо:**
```python
# Перед отчётом запустить тест:
from sqlalchemy import Result, ScalarResult
import inspect
print(inspect.signature(Result.scalar_one))  # (self) -> 'Any' — нет async
```

---

### 2. Pydantic Optional поля — 14 ложных срабатываний

**Проблема:** Флагил `field: str | None` без `default=None` как "CRITICAL — будет ValidationError"

**Причина:** Не учитывался паттерн `from_attributes=True` + SQLAlchemy ORM:
```python
class Response(BaseModel):
    optional: str | None  # без default=None
    model_config = ConfigDict(from_attributes=True)

# SQLAlchemy объект ВСЕГДА имеет атрибут (даже NULL)
obj = PlacementDispute()
obj.optional = None  # ← атрибут есть, значение None

Response.model_validate(obj)  # ✓ УСПЕХ — нет ValidationError
```

**Урок:**
- Pydantic v2 + `from_attributes=True` + SQLAlchemy = работает корректно
- Optional без default — не CRITICAL, а best practice рекомендация

**Как надо:**
```python
# Перед отчётом запустить тест:
class Test(BaseModel):
    opt: str | None
    model_config = ConfigDict(from_attributes=True)

class Obj: opt = None; id = 1
Test.model_validate(Obj())  # Проверить что нет ошибки
```

---

### 3. Безопасность — 8 ложных срабатываний

**Проблема:** Флагил admin endpoints как "без авторизации" потому что нет `current_user: User`

**Причина:** AST искал только `current_user` в аргументах, не понимая паттерны FastAPI:
```python
# Паттерн 1: Прямая зависимость
@admin_router.get("/admin")
async def endpoint(admin: Annotated[User, Depends(get_current_admin_user)]): ...

# Паттерн 2: Type alias
AdminUser = Annotated[User, Depends(get_current_admin_user)]

@admin_router.get("/admin")
async def endpoint(admin_user: AdminUser): ...  # ← ТОЖЕ авторизация!
```

**Урок:**
- `Annotated[User, Depends(...)]` = авторизация ✓
- Type aliases (`AdminUser`, `CurrentUser`) = тоже авторизация ✓
- Проверять импорты: `from dependencies import AdminUser`

**Как надо:**
```python
# Перед отчётом проверить зависимости:
grep -n "AdminUser = Annotated" src/api/dependencies.py
grep -n "get_current_admin_user" src/api/routers/*.py
```

---

## Рекомендации для будущих code review

### 1. Контекстный AST-анализ

```python
# НЕПРАВИЛЬНО:
for node in ast.walk(tree):
    if isinstance(node, ast.Call) and node.func.attr in ['scalar', 'scalar_one']:
        if not has_await(node): flag_issue()  # ← ЛОЖНОЕ срабатывание!

# ПРАВИЛЬНО:
ASYNC_METHODS = {'execute', 'scalars'}  # только эти требуют await
SYNC_RESULT_METHODS = {'scalar', 'scalar_one', 'all'}  # синхронные

for node in ast.walk(tree):
    if isinstance(node, ast.Call):
        method = node.func.attr
        if method in ASYNC_METHODS and not has_await(node):
            flag_issue()  # ← Реальная проблема
        if method in SYNC_RESULT_METHODS:
            skip()  # ← Это нормально
```

### 2. Верификация через запуск кода

```python
# Перед тем как флагить как CRITICAL:
def verify_pydantic_optional():
    from pydantic import BaseModel, ConfigDict
    
    class Test(BaseModel):
        opt: str | None
        model_config = ConfigDict(from_attributes=True)
    
    class Obj:
        opt = None
    
    try:
        Test.model_validate(Obj())
        return "WORKS"  # ← Не CRITICAL!
    except ValidationError:
        return "REAL_ISSUE"
```

### 3. Понимание архитектурных паттернов

| Паттерн | Выглядит как | На самом деле |
|---------|--------------|---------------|
| `AdminUser = Annotated[User, Depends(...)]` | "нет auth" | ✓ Авторизация |
| `Result.scalar_one()` | "missing await" | ✓ Синхронный метод |
| `Optional` без default | "ValidationError" | ✓ Работает с ORM |

### 4. Градация severity

**НЕ флагить как CRITICAL если:**
- Не запущен тест на воспроизведение
- Не проверена документация библиотеки
- Не учтён архитектурный контекст

**Правильная градация:**
```
CRITICAL → Падение в продакшне (500), потеря данных
  ↓
HIGH → Некорректное поведение, но есть workaround
  ↓
MEDIUM → Best practice violation, не ломает функционал
  ↓
LOW → Code style, consistency
```

---

## Чек-лист перед сохранением отчёта

- [ ] Запустил тест на воспроизведение проблемы?
- [ ] Проверил документацию библиотеки (SQLAlchemy, Pydantic, FastAPI)?
- [ ] Учёл архитектурные паттерны проекта?
- [ ] Проверил что dependency импортируется правильно?
- [ ] Не перепутал sync/async методы?
- [ ] Severity соответствует реальному impact?

---

## Итоговая статистика этого review

| Категория | Найдено | Ложные | Реальные |
|-----------|---------|--------|----------|
| Async/Await | 142 | 142 | 0 |
| Pydantic | 22 | 14 | 8 |
| Security | 15 | 8 | 0 (все защищены) |
| Repositories | 12 | 0 | 12 (5 CRITICAL) |
| Error Handling | 12 | 0 | 12 (2 HIGH) |
| **ИТОГО** | **203** | **164** | **39** |

**Вывод:** 81% первоначальных "проблем" были ложными срабатываниями из-за недостаточного контекстного анализа.

---

## Action Items для улучшения tooling

1. [ ] Добавить проверку контекста для SQLAlchemy Result методов
2. [ ] Добавить распознавание FastAPI Depends паттернов
3. [ ] Добавить auto-test для Pydantic схем перед флаггингом
4. [ ] Требовать минимум 2 подтверждения перед CRITICAL severity
5. [ ] Добавить этап manual verification перед сохранением отчёта
