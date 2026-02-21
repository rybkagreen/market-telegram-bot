# Skills — Market Telegram Bot

> **What are Skills?**
> Skills are self-contained instruction packages for Qwen Code (and compatible agents like Claude Code, GitHub Copilot).
> Each skill lives in its own subdirectory with a `SKILL.md` file (YAML frontmatter + instructions).
> The agent reads the `name` and `description` at startup to decide which skill is relevant,
> then loads the full body only when needed — keeping context windows efficient.
>
> Official spec: [agentskills.io/specification](https://agentskills.io/specification)
> Qwen Code docs: [github.com/QwenLM/qwen-code](https://github.com/QwenLM/qwen-code)

---

## Directory Layout

Skills for this project live in `.qwen/skills/` (project-scoped) or `~/.qwen/skills/` (global, for reuse across projects).

```
.qwen/
└── skills/
    ├── python-async/
    │   └── SKILL.md
    ├── aiogram-handler/
    │   └── SKILL.md
    ├── sqlalchemy-repository/
    │   └── SKILL.md
    ├── celery-task/
    │   └── SKILL.md
    ├── content-filter/
    │   └── SKILL.md
    ├── fastapi-router/
    │   └── SKILL.md
    ├── react-mini-app/
    │   └── SKILL.md
    ├── docker-compose/
    │   └── SKILL.md
    └── pytest-async/
        └── SKILL.md
```

> **Symlink tip** (cross-agent compatibility):
> ```bash
> ln -s .qwen/skills .claude/skills     # also available in Claude Code
> ln -s .qwen/skills .gemini/skills     # also available in Gemini CLI
> ```

---

## SKILL.md Format Reference

Every `SKILL.md` must follow this structure exactly:

```markdown
---
name: skill-name-in-kebab-case
description: >
  One-paragraph description of what this skill does and WHEN to invoke it.
  Be specific: include trigger keywords, file types, task categories.
  Max 1024 characters. Written in third person. No XML tags.
license: MIT
---

# Skill Title

Brief prose explanation of the skill's purpose.

## When to Use
- Bullet list of specific triggers

## Instructions
Step-by-step instructions written for the AI, not the human.

## Examples
Concrete input → output demonstrations.
```

**Frontmatter rules (from official spec):**

| Field | Required | Rules |
|---|---|---|
| `name` | ✅ | Max 64 chars, `lowercase-kebab-case`, must match parent directory name |
| `description` | ✅ | Max 1024 chars, no XML tags, written in third person |
| `license` | optional | Short SPDX identifier or filename |
| `version` | optional | Semver string |
| `author` | optional | Author name or org |

---

## Project Skills Catalogue

### 1. `python-async`

**Triggers:** writing any `async def` function, `asyncio`, `await` patterns in Python 3.13

```markdown
---
name: python-async
description: >
  Generates correct async Python 3.13 code for this project.
  Use when writing or editing any async function, coroutine, context manager,
  or asyncio pattern. Enforces project conventions: no blocking calls in
  async context, proper exception handling, type hints on all signatures.
---

# Python Async Conventions

## Rules
- All I/O must be `await`-ed — never call blocking functions inside `async def`
- Use `asyncio.gather()` for concurrent tasks, `asyncio.sleep()` for delays
- Always add return type hint: `async def foo() -> ReturnType:`
- Use `async with` for context managers (sessions, locks, HTTP clients)
- Catch specific exceptions, never bare `except:`

## Pattern: async generator
```python
async def stream_results(ids: list[int]) -> AsyncIterator[Result]:
    async with get_session() as session:
        for chunk in chunks(ids, size=100):
            results = await session.execute(select(Model).where(Model.id.in_(chunk)))
            for row in results.scalars():
                yield row
```
```

---

### 2. `aiogram-handler`

**Triggers:** writing bot handlers, FSM states, callbacks, commands, middlewares

```markdown
---
name: aiogram-handler
description: >
  Creates aiogram 3.x Telegram bot handlers, FSM state machines, callback
  handlers, and middlewares following this project's conventions.
  Use when writing /command handlers, inline keyboard callbacks, FSM wizard
  steps, or any bot-facing code in src/bot/handlers/ or src/bot/states/.
  Enforces: no DB access in handlers, call services only, throttling via Redis.
---

# aiogram 3 Handler Conventions

## Rules
- Handlers NEVER access DB directly — call `service.method()` or `repo.method()`
- All handlers must be `async def`
- Register with `@router.message()` or `@router.callback_query()`
- Use `CallbackData` factory for all inline keyboard callbacks
- Use `ParseMode.HTML` for formatted messages — never Markdown
- Handle errors gracefully: catch exceptions, notify user with friendly message

## FSM Pattern
```python
class MyStates(StatesGroup):
    step_one = State()
    step_two = State()

@router.message(MyStates.step_one)
async def handle_step_one(message: Message, state: FSMContext) -> None:
    await state.update_data(field=message.text)
    await state.set_state(MyStates.step_two)
    await message.answer("Step 2:", reply_markup=get_step_kb(back=True))

@router.callback_query(MyStates.step_two, F.data == "back")
async def handle_back(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(MyStates.step_one)
    await callback.message.edit_text("Step 1:", reply_markup=get_step_kb())
```

## Keyboard Pattern
```python
from aiogram.filters.callback_data import CallbackData

class ActionCB(CallbackData, prefix="action"):
    name: str
    value: int

def get_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Click", callback_data=ActionCB(name="test", value=1))
    return builder.as_markup()
```
```

---

### 3. `sqlalchemy-repository`

**Triggers:** writing DB models, repositories, queries, migrations

```markdown
---
name: sqlalchemy-repository
description: >
  Creates SQLAlchemy 2.0 async repositories, models, and queries following
  the project's Repository pattern. Use when writing new DB models in
  src/db/models/, new repository methods in src/db/repositories/, or
  composing complex async queries. Enforces: Generic BaseRepository[T],
  asyncpg driver, no ORM lazy-loading, atomic balance updates with RETURNING.
---

# SQLAlchemy 2.0 Async Conventions

## Rules
- All queries use `await session.execute(select(...))`
- Never use lazy relationships — always `selectinload` or `joinedload`
- Atomic updates: use `UPDATE ... RETURNING` for balance changes
- Use `upsert` (`insert().on_conflict_do_update()`) for bulk chat imports
- Session is always injected — repositories never create their own sessions

## Repository Pattern
```python
from typing import Generic, TypeVar
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")

class BaseRepository(Generic[T]):
    model: type[T]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, id: int) -> T | None:
        return await self.session.get(self.model, id)

    async def create(self, **data) -> T:
        obj = self.model(**data)
        self.session.add(obj)
        await self.session.flush()
        return obj
```

## Atomic Balance Update
```python
from sqlalchemy import update
from decimal import Decimal

async def update_balance(self, user_id: int, delta: Decimal) -> Decimal:
    stmt = (
        update(User)
        .where(User.id == user_id, User.balance + delta >= 0)
        .values(balance=User.balance + delta)
        .returning(User.balance)
    )
    result = await self.session.execute(stmt)
    new_balance = result.scalar_one_or_none()
    if new_balance is None:
        raise InsufficientBalanceError()
    return new_balance
```
```

---

### 4. `celery-task`

**Triggers:** writing Celery tasks, scheduled jobs, async queue workers

```markdown
---
name: celery-task
description: >
  Creates Celery 5 tasks and Beat schedules for this project's async
  task queue. Use when adding new background tasks in src/tasks/,
  configuring periodic jobs in celery_config.py, or handling task
  retries and error cases. Enforces: bind=True for retries, acks_late,
  separate queues for mailing vs parser tasks, exponential backoff.
---

# Celery Task Conventions

## Rules
- Use `bind=True` for all tasks that may need `self.retry()`
- Route mailing tasks to `queue="mailing"`, parser tasks to `queue="parser"`
- Max retries: 3, countdown: exponential (1s, 4s, 9s)
- Always `acks_late=True` at app level — tasks re-queue on worker crash
- Log task start/end with `logger.info()` including task ID

## Task Pattern
```python
from src.tasks.celery_app import app
import logging

logger = logging.getLogger(__name__)

@app.task(bind=True, max_retries=3, queue="mailing")
def send_campaign(self, campaign_id: int) -> dict:
    logger.info("Task %s: starting campaign %d", self.request.id, campaign_id)
    try:
        result = run_async(mailing_service.run_campaign(campaign_id))
        logger.info("Task %s: campaign %d done — %s", self.request.id, campaign_id, result)
        return result
    except FloodWaitError as exc:
        raise self.retry(exc=exc, countdown=exc.value + 5)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
```
```

---

### 5. `content-filter`

**Triggers:** checking text for prohibited content, moderation, stop-word filtering

```markdown
---
name: content-filter
description: >
  Applies the project's 3-level content moderation pipeline to text.
  Use when checking advertising text before sending, testing filter rules,
  adding new stop-word categories, or extending the moderation service.
  Pipeline: Level 1 regex → Level 2 pymorphy3 morphology → Level 3 LLM.
  Returns FilterResult(passed, score, categories, flagged_fragments).
---

# Content Filter — 3-Level Pipeline

## Categories (stopwords_ru.json)
`drugs` · `terrorism` · `weapons` · `adult` · `fraud` · `suicide` · `extremism` · `gambling`

## Usage
```python
from src.utils.content_filter.filter import ContentFilter
from src.config.settings import settings

cf = ContentFilter(settings)
result = await cf.check("your ad text here")

if not result.passed:
    # result.categories → ["drugs"]
    # result.flagged_fragments → ["закладка", "героин"]
    # result.score → 0.87
```

## Adding a New Category
1. Add key + word list to `stopwords_ru.json`
2. Add regex patterns for common misspellings
3. Add 10+ unit tests in `tests/unit/test_content_filter.py`
4. Run: `pytest tests/unit/test_content_filter.py -v`
```

---

### 6. `fastapi-router`

**Triggers:** writing FastAPI routes, Pydantic schemas, API endpoints, dependencies

```markdown
---
name: fastapi-router
description: >
  Creates FastAPI routers, Pydantic v2 schemas, and dependency injection
  for the Mini App backend in src/api/. Use when adding new API endpoints,
  writing request/response schemas, or implementing authentication dependencies.
  Enforces: JWT via Telegram initData HMAC-SHA256, Pydantic v2 models,
  async route handlers, proper HTTP status codes.
---

# FastAPI Router Conventions

## Rules
- All route handlers must be `async def`
- Always use Pydantic v2 models for request/response (`model_config = ConfigDict(from_attributes=True)`)
- Inject `current_user: User = Depends(get_current_user)` for protected routes
- Return meaningful HTTP status codes: 200, 201, 400, 401, 403, 404, 422
- No business logic in routers — delegate to services

## Router Pattern
```python
from fastapi import APIRouter, Depends, HTTPException, status
from src.api.dependencies import get_current_user, get_db
from src.db.models.user import User

router = APIRouter(prefix="/campaigns", tags=["campaigns"])

@router.get("", response_model=list[CampaignResponse])
async def list_campaigns(
    page: int = 1,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db),
) -> list[CampaignResponse]:
    campaigns = await campaign_repo.get_by_user(current_user.id, page=page)
    return [CampaignResponse.model_validate(c) for c in campaigns]
```

## Pydantic v2 Schema Pattern
```python
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from decimal import Decimal

class CampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    status: str
    created_at: datetime
```
```

---

### 7. `react-mini-app`

**Triggers:** writing Mini App components, Telegram WebApp integration, TypeScript React

```markdown
---
name: react-mini-app
description: >
  Creates React TypeScript components for the Telegram Mini App in mini_app/src/.
  Use when writing new pages, UI components, or Telegram WebApp integrations.
  Enforces: glassmorphism design (backdrop-filter blur), Tailwind CSS utility classes,
  @twa-dev/sdk for Telegram integration, zustand for state, recharts for charts,
  react-router-dom for navigation, dark/light theme via Telegram.WebApp.colorScheme.
---

# React Mini App Conventions

## Rules
- All API calls go through `src/api/client.ts` (axios with JWT interceptor)
- Read theme: `const { colorScheme } = useTelegramWebApp()` — apply dark CSS vars accordingly
- Glassmorphism card: `backdrop-filter: blur(12px); background: rgba(255,255,255,0.1)`
- No inline styles except glassmorphism — use Tailwind utility classes
- All data fetching via custom hooks (`useCampaigns`, `useAnalytics`, etc.)
- Show loading skeleton while data fetches, error boundary for failures

## GlassCard Component
```tsx
interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
}

export const GlassCard: React.FC<GlassCardProps> = ({ children, className = "" }) => (
  <div
    className={`rounded-2xl p-4 border border-white/20 ${className}`}
    style={{ background: "rgba(255,255,255,0.1)", backdropFilter: "blur(12px)" }}
  >
    {children}
  </div>
);
```

## useTelegramWebApp Hook
```tsx
import { useEffect } from "react";

export function useTelegramWebApp() {
  const tg = window.Telegram?.WebApp;
  useEffect(() => {
    tg?.ready();
    tg?.expand();
  }, []);
  return {
    tg,
    user: tg?.initDataUnsafe?.user,
    colorScheme: tg?.colorScheme ?? "light",
    initData: tg?.initData ?? "",
  };
}
```
```

---

### 8. `docker-compose`

**Triggers:** editing Docker Compose files, Dockerfiles, Nginx config, container setup

```markdown
---
name: docker-compose
description: >
  Creates and edits Docker Compose configurations, Dockerfiles, and Nginx
  configs for this project. Use when adding new services, modifying container
  resources, configuring Nginx routing, or updating production docker-compose.prod.yml.
  Enforces: multi-stage Python builds with Poetry, healthchecks for postgres and redis,
  restart: unless-stopped in prod, resource limits, named volumes.
---

# Docker Compose Conventions

## Rules
- Local: `docker-compose.yml` — postgres + redis with exposed ports
- Production: `docker-compose.prod.yml` — all services, restart policies, resource limits
- All Python images: `python:3.13-slim`, multi-stage with `poetry install --only=main`
- Always add `healthcheck` for postgres and redis
- Use named volumes for postgres data persistence
- Nginx: upstream blocks for bot (port 8000) and api (port 8001)

## Service Template
```yaml
services:
  bot:
    build:
      context: .
      dockerfile: docker/Dockerfile.bot
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 512m
```
```

---

### 9. `pytest-async`

**Triggers:** writing tests, pytest fixtures, testcontainers, async test patterns

```markdown
---
name: pytest-async
description: >
  Creates async pytest tests following this project's testing conventions.
  Use when writing unit tests for services/filters, integration tests for
  repositories with real PostgreSQL via testcontainers, or API tests with
  FastAPI TestClient. Enforces: pytest-asyncio, testcontainers for integration
  tests, mock for external services (Telegram API, Claude API, YooKassa).
---

# Pytest Async Conventions

## Rules
- Mark all async tests: `@pytest.mark.asyncio`
- Unit tests: mock ALL external calls (DB, Redis, APIs)
- Integration tests: use `testcontainers` (real PostgreSQL + Redis in Docker)
- Never use production `.env` in tests — use `pytest-dotenv` with `.env.test`
- Aim for: >80% coverage on services, 100% on critical paths (billing, filter)

## Async Fixture Pattern
```python
import pytest
from testcontainers.postgres import PostgresContainer
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16") as pg:
        yield pg

@pytest.fixture
async def async_session(postgres_container):
    engine = create_async_engine(postgres_container.get_connection_url())
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = async_sessionmaker(engine)
    async with async_session() as session:
        yield session

@pytest.mark.asyncio
async def test_create_user(async_session):
    repo = UserRepository(async_session)
    user = await repo.create_or_update(telegram_id=123456, username="testuser")
    assert user.telegram_id == 123456
```
```

---

## Enabling Skills in Qwen Code

### Project-level (recommended for this repo)

```bash
# Create the skills directory
mkdir -p .qwen/skills

# Enable experimental skills feature in project settings
cat > .qwen/settings.json << 'EOF'
{
  "experimental": {
    "skills": {
      "enabled": true
    }
  },
  "context": {
    "fileName": ["QWEN.md"],
    "loadFromIncludeDirectories": true
  }
}
EOF
```

### Launch with skills enabled

```bash
qwen --experimental-skills
```

### Verify skills are loaded

```
/skills          # list all available skills
/memory show     # verify QWEN.md is loaded
```

---

## Skill Authoring Checklist

Before committing a new skill to `.qwen/skills/`:

- [ ] `SKILL.md` is at the root of the skill directory (not nested deeper)
- [ ] `name` field matches the parent directory name (kebab-case, max 64 chars)
- [ ] `description` is under 1024 chars and answers "what does it do + when to use it"
- [ ] `description` is written in third person
- [ ] `SKILL.md` body is under 500 lines (move details to `references/` if longer)
- [ ] Code examples in the body are wrapped in fenced code blocks with language tag
- [ ] No secrets or credentials in any skill file
- [ ] Tested: run Qwen Code and verify the skill triggers on expected prompts
- [ ] Run `/skills` to confirm the skill appears in the list

---

## Cross-Agent Compatibility

Skills in this project follow the [Agent Skills open standard](https://agentskills.io/specification) and are compatible with:

| Agent | Skills directory | Notes |
|---|---|---|
| **Qwen Code** | `.qwen/skills/` | `--experimental-skills` flag required |
| **Claude Code** | `.claude/skills/` | Native support |
| **GitHub Copilot** | `.github/skills/` | VS Code agent mode |
| **OpenCode** | `.opencode/skills/` | Native support |

To make skills available to all agents simultaneously:

```bash
# Create one canonical skills dir, symlink to all agents
mkdir -p skills
ln -sf ../skills .qwen/skills
ln -sf ../skills .claude/skills
ln -sf ../skills .github/skills
```

---

## References

- [Qwen Code — GitHub](https://github.com/QwenLM/qwen-code)
- [Qwen Code — Configuration docs](https://qwenlm.github.io/qwen-code-docs/en/cli/configuration/)
- [Qwen Code — Memory / QWEN.md](https://github.com/QwenLM/qwen-code/blob/main/docs/cli/memory.md)
- [Agent Skills Specification](https://agentskills.io/specification)
- [Skill authoring best practices — Anthropic](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
- [Claude Code Skills deep dive](https://mikhail.io/2025/10/claude-code-skills/)
