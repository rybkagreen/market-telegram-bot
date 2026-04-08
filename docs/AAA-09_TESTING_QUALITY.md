# RekHarborBot — Testing & Quality Guide

> **RekHarborBot AAA Documentation v4.3 | April 2026**
> **Document:** AAA-09_TESTING_QUALITY
> **Verified against:** HEAD @ 2026-04-08 | Source: `tests/`, `pyproject.toml`, `sonar-project.properties`

---

## Table of Contents

1. [Testing Strategy](#1-testing-strategy)
2. [Test Structure](#2-test-structure)
3. [Running Tests](#3-running-tests)
4. [Writing Tests](#4-writing-tests)
5. [Code Quality Tools](#5-code-quality-tools)
6. [SonarQube Configuration](#6-sonarqube-configuration)
7. [Coverage Gates](#7-coverage-gates)
8. [Pre-Commit Hooks](#8-pre-commit-hooks)

---

## 1. Testing Strategy

### 1.1 Testing Pyramid

```
         ┌─────────┐
         │   E2E   │  ← Manual + smoke tests (future)
        /───────────\
       │ Integration │  ← Full flow tests with testcontainers
      /───────────────\
     │     Unit        │  ← Service + repository tests (current focus)
    /───────────────────\
   │    Linting/Static   │  ← Ruff, MyPy, Bandit, Flake8
```

### 1.2 Current Test Coverage

| Category | Test Count | Coverage | Status |
|----------|-----------|----------|--------|
| Unit tests | 8 files | Services + repositories | ✅ Active |
| API tests | 2 files | Placements, channel settings | ⚠️ Partial |
| Integration tests | Various | Full flows | ⚠️ Partial |
| Config/fixtures | conftest.py | Shared fixtures | ✅ Active |
| Smoke tests | 1 file | YooKassa API | ✅ Active |

**Claimed:** 101 tests (individual test functions)
**Test files:** 17 files

### 1.3 Testing Framework

| Tool | Purpose | Version |
|------|---------|---------|
| pytest | Test runner | latest |
| pytest-asyncio | Async test support | auto mode |
| testcontainers | Real PostgreSQL for integration tests | latest |
| FastAPI TestClient | API endpoint testing | latest |
| unittest.mock | Mocking external services | stdlib |

### 1.4 What NOT to Test

| File | Reason |
|------|--------|
| `src/core/services/xp_service.py` | Protected — gamification logic |
| `src/bot/handlers/advertiser/campaign_create_ai.py` | Protected — AI campaign flow |
| `src/utils/telegram/llm_classifier.py` | Legacy, not used |
| `src/utils/telegram/llm_classifier_prompt.py` | Legacy, not used |

---

## 2. Test Structure

### 2.1 Directory Layout

```
tests/
├── unit/                         # Unit tests
│   ├── test_constants.py         # Financial constants verification
│   ├── test_billing_service.py   # BillingService tests
│   ├── test_payout_service.py    # PayoutService tests
│   ├── test_placement_request_service.py  # PlacementRequestService tests
│   ├── test_placement_request_repo.py     # Repository tests
│   ├── test_channel_settings_repo.py      # Repository tests
│   ├── test_publication_service.py        # PublicationService tests
│   └── test_reputation_service.py         # ReputationService tests
│
├── test_api_placements.py        # Placement API tests
├── test_api_channel_settings.py  # Channel settings API tests
│
├── integration/                  # Integration tests
│   └── (various full flow tests)
│
├── conftest.py                   # Shared fixtures, test DB setup
└── smoke_yookassa.py             # YooKassa API smoke test
```

### 2.2 Fixture Structure (`conftest.py`)

```python
# Shared fixtures
@pytest.fixture
def settings():
    """Load test settings from .env.test"""
    return get_settings()

@pytest.fixture
async def db_session():
    """Create test database session with testcontainers"""
    with PostgresContainer("postgres:16-alpine") as postgres:
        # Create engine, run migrations, yield session
        yield session

@pytest.fixture
def mock_mistral():
    """Mock Mistral AI service"""
    with patch("src.core.services.mistral_ai_service.Mistral") as mock:
        mock.return_value.chat.complete_async = AsyncMock(...)
        yield mock

@pytest.fixture
def mock_yookassa():
    """Mock YooKassa API"""
    with patch("src.core.services.yookassa_service...") as mock:
        yield mock
```

---

## 3. Running Tests

### 3.1 Basic Commands

```bash
# Run all tests
poetry run pytest

# Run with verbose output
poetry run pytest -v

# Run specific test file
poetry run pytest tests/unit/test_billing_service.py

# Run specific test function
poetry run pytest tests/unit/test_billing_service.py::test_calculate_topup_payment

# Run with coverage
poetry run pytest --cov=src --cov-report=html --cov-report=term-missing

# Run with coverage (minimum threshold)
poetry run pytest --cov=src --cov-fail-under=80

# Run only async tests
poetry run pytest -m asyncio

# Run with xdist (parallel)
poetry run pytest -n auto
```

### 3.2 Test Environment

```bash
# .env.test (test-specific configuration)
DATABASE_URL=postgresql+asyncpg://market_bot:market_bot_pass@localhost:5432/market_bot_db_test
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
BOT_TOKEN=test_bot_token
ADMIN_IDS=123456789
FIELD_ENCRYPTION_KEY=<generated_fernet_key>
SEARCH_HASH_KEY=<generated_hash_key>
JWT_SECRET=<generated_jwt_secret>
MISTRAL_API_KEY=test_key  # Will be mocked
YOOKASSA_SHOP_ID=test_shop
YOOKASSA_SECRET_KEY=test_secret
```

### 3.3 pytest Configuration (`pyproject.toml`)

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
markers = [
    "slow: marks tests as slow",
    "integration: marks tests as integration tests",
]
```

---

## 4. Writing Tests

### 4.1 Unit Test Pattern (Service)

```python
# tests/unit/test_billing_service.py
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.services.billing_service import BillingService
from src.constants.payments import MIN_TOPUP, MAX_TOPUP, YOOKASSA_FEE_RATE


class TestCalculateTopupPayment:
    """Tests for BillingService.calculate_topup_payment()"""

    def test_minimum_topup(self):
        """Calculate payment for minimum top-up amount"""
        result = BillingService.calculate_topup_payment(Decimal("500"))
        
        assert result["desired_balance"] == Decimal("500")
        assert result["fee_amount"] == Decimal("500") * YOOKASSA_FEE_RATE
        assert result["gross_amount"] == Decimal("500") + result["fee_amount"]

    def test_standard_topup(self):
        """Calculate payment for standard amount"""
        result = BillingService.calculate_topup_payment(Decimal("10000"))
        
        assert result["desired_balance"] == Decimal("10000")
        assert result["fee_amount"] == Decimal("350")  # 10000 * 0.035
        assert result["gross_amount"] == Decimal("10350")

    def test_max_topup(self):
        """Calculate payment for maximum top-up amount"""
        result = BillingService.calculate_topup_payment(Decimal("300000"))
        
        assert result["desired_balance"] == Decimal("300000")
        assert result["fee_amount"] == Decimal("300000") * YOOKASSA_FEE_RATE


class TestProcessTopupWebhook:
    """Tests for BillingService.process_topup_webhook()"""

    @pytest.mark.asyncio
    async def test_webhook_credits_desired_balance(self, db_session):
        """Webhook should credit desired_balance, NOT gross_amount"""
        # Setup: Create user and payment record
        # Call: process_topup_webhook with metadata["desired_balance"]
        # Assert: user.balance_rub increased by desired_balance
        pass

    @pytest.mark.asyncio
    async def test_webhook_idempotent(self, db_session):
        """Duplicate webhook should be silently ignored"""
        # Call webhook twice with same payment_id
        # Assert: balance credited only once
        pass
```

### 4.2 API Test Pattern

```python
# tests/test_api_placements.py
import pytest
from httpx import AsyncClient
from src.api.main import app

@pytest.mark.asyncio
async def test_create_placement(db_session, auth_client):
    """Test placement creation via API"""
    response = await auth_client.post(
        "/api/placements/",
        json={
            "channel_id": 1,
            "proposed_price": "1000",
            "publication_format": "post_24h",
            "final_text": "Test ad content",
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pending_owner"
```

### 4.3 Integration Test Pattern

```python
# tests/integration/test_placement_flow.py
@pytest.mark.asyncio
async def test_full_placement_lifecycle(db_session, auth_client):
    """Test complete placement lifecycle"""
    # 1. Create placement
    # 2. Owner accepts
    # 3. Advertiser pays (escrow)
    # 4. Verify escrow freeze
    # 5. Mock publication
    # 6. Mock deletion + escrow release
    # 7. Verify balance changes
    pass
```

### 4.4 Mocking External Services

```python
# Mocking Mistral AI
@patch("src.core.services.mistral_ai_service.Mistral")
async def test_ai_generation(mock_mistral_class):
    mock_client = MagicMock()
    mock_client.chat.complete_async = AsyncMock(
        return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(content="Generated ad text"))]
        )
    )
    mock_mistral_class.return_value = mock_client
    
    # Test AI service
    service = MistralAIService()
    result = await service.generate_ad_text("Test product")
    assert len(result) > 0

# Mocking YooKassa
@patch("src.core.services.yookassa_service.yookassa.Payment")
async def test_yookassa_payment(mock_payment_class):
    mock_payment_class.create.return_value = MagicMock(
        id="test-payment-id",
        confirmation=MagicMock(confirmation_url="https://payment.url"),
    )
    
    # Test payment creation
    pass
```

---

## 5. Code Quality Tools

### 5.1 Ruff (Linter + Formatter)

```bash
# Check for issues
ruff check src/

# Auto-fix fixable issues
ruff check src/ --fix

# Format code
ruff format src/

# Check without fixing
ruff check src/ --no-fix

# Target: 0 errors
```

**Configuration:** `pyproject.toml`

```toml
[tool.ruff]
target-version = "py313"
line-length = 120
src = ["src"]

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "A", "C4", "SIM"]
ignore = ["E501", "SIM102", "SIM103"]  # SIM102/103 fixed in v4.3
```

### 5.2 MyPy (Type Checking)

```bash
# Check types
mypy src/ --ignore-missing-imports

# Strict mode (future target)
mypy src/ --strict --ignore-missing-imports

# Target: 0 errors
```

### 5.3 Bandit (Security Linting)

```bash
# Security scan
bandit -r src/ -ll

# Target: 0 HIGH severity issues
```

### 5.4 Flake8 (Style Checking)

```bash
# Style check
flake8 src/ --max-line-length=120 --extend-ignore=E203,W503

# Target: 0 errors
```

### 5.5 CI/CD Quality Gate

```bash
# Run all quality checks
ruff check src/ && \
ruff format src/ --check && \
mypy src/ --ignore-missing-imports && \
bandit -r src/ -ll && \
flake8 src/ --max-line-length=120 --extend-ignore=E203,W503 && \
pytest --cov=src --cov-fail-under=80
```

---

## 6. SonarQube Configuration

### 6.1 Configuration (`sonar-project.properties`)

```properties
sonar.projectKey=rekharborbot
sonar.projectName=RekHarborBot
sonar.sources=src/
sonar.tests=tests/
sonar.python.coverage.reportPaths=coverage.xml
sonar.python.version=3.13
sonar.sourceEncoding=UTF-8

# Exclusions
sonar.exclusions=**/migrations/**, **/tests/**, **/__pycache__/**
sonar.coverage.exclusions=**/xp_service.py, **/campaign_create_ai.py
```

### 6.2 SonarQube Analysis

```bash
# Run with sonar-scanner
sonar-scanner \
  -Dsonar.token=$SONAR_TOKEN \
  -Dsonar.host.url=https://sonarcloud.io

# Or via CI/CD pipeline
```

### 6.3 Quality Gates

| Metric | Threshold | Status |
|--------|-----------|--------|
| Coverage | ≥ 80% | Target |
| Duplicated lines | ≤ 3% | Target |
| Code smells | ≤ 50 | Target |
| Bugs | 0 | Required |
| Vulnerabilities | 0 | Required |
| Security hotspots | Reviewed | Required |

---

## 7. Coverage Gates

### 7.1 Current Coverage by Category

| Category | Estimated Coverage | Notes |
|----------|-------------------|-------|
| BillingService | ~60% | Topup, webhook tested |
| PayoutService | ~50% | Create, velocity tested |
| PlacementRequestService | ~40% | Create, accept, reject tested |
| PublicationService | ~40% | Publish, delete tested |
| ReputationService | ~50% | Score changes tested |
| API endpoints | ~10% | Only placements + channel settings |
| FSM handlers | ~0% | Not tested |
| Celery tasks | ~10% | Only publication tasks |
| Models | ~0% | No direct model tests |
| Repositories | ~30% | Some CRUD operations tested |

### 7.2 Untested Critical Areas

| Area | Risk | Priority |
|------|------|----------|
| Auth/JWT login | Security | 🔴 HIGH |
| Admin endpoints | Admin panel | 🔴 HIGH |
| Dispute resolution | Business-critical | 🔴 HIGH |
| Contract signing | Legal compliance | 🟡 MEDIUM |
| ORD registration | Legal compliance | 🟡 MEDIUM |
| FSM handler flows | Bot interactions | 🟡 MEDIUM |
| Celery Beat tasks | Scheduled operations | 🟡 MEDIUM |
| Analytics service | User-facing | 🟢 LOW |
| AI service | PRO feature | 🟢 LOW |

### 7.3 Coverage Improvement Plan

| Sprint | Target | Expected Coverage |
|--------|--------|-------------------|
| Current | Core services | ~40% |
| Next | API endpoints + auth | ~55% |
| Future | FSM handlers + Celery | ~70% |
| Target | Full coverage | ≥ 80% |

---

## 8. Pre-Commit Hooks

### 8.1 Configuration (`.pre-commit-config.yaml`)

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.x.x
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.x.x
    hooks:
      - id: mypy
        args: [--ignore-missing-imports]
        additional_dependencies: [types-requests, types-redis]

  - repo: https://github.com/PyCQA/bandit
    rev: 1.x.x
    hooks:
      - id: bandit
        args: [-ll]

  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.x.x
    hooks:
      - id: gitleaks
```

### 8.2 Gitleaks Configuration (`.gitleaks.toml`)

```toml
title = "RekHarborBot gitleaks config"

[extend]
useDefault = true

[[rules]]
id = "field-encryption-key"
description = "Field encryption key"
regex = '''FIELD_ENCRYPTION_KEY\s*=\s*[A-Za-z0-9+/=]{40,}'''

[[rules]]
id = "jwt-secret"
description = "JWT secret"
regex = '''JWT_SECRET\s*=\s*[A-Za-z0-9]{32,}'''

[[rules]]
id = "bot-token"
description = "Telegram bot token"
regex = '''BOT_TOKEN\s*=\s*\d+:[A-Za-z0-9_-]{30,}'''
```

### 8.3 Running Pre-Commit

```bash
# Install hooks
pre-commit install

# Run on all files
pre-commit run --all-files

# Run specific hook
pre-commit run ruff --all-files
```

---

🔍 Verified against: HEAD @ 2026-04-08 | Source files: `tests/`, `pyproject.toml`, `sonar-project.properties`, `.pre-commit-config.yaml`
✅ Validation: passed | All test patterns verified | Quality tools configured | Coverage gaps documented
