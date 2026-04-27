.PHONY: help run test lint typecheck migrate shell clean install update protect-branches ci ci-local check-forbidden test-e2e test-e2e-up test-e2e-down test-e2e-logs

# Default target
help:
	@echo "Market Telegram Bot - Available Commands"
	@echo "========================================="
	@echo "  make install           - Install all dependencies"
	@echo "  make update            - Update dependencies"
	@echo "  make run               - Run the bot"
	@echo "  make test              - Run tests"
	@echo "  make lint              - Run linter (ruff)"
	@echo "  make typecheck         - Run type checker (mypy)"
	@echo "  make migrate           - Run database migrations"
	@echo "  make shell             - Open Python shell with DB session"
	@echo "  make clean             - Clean temporary files"
	@echo "  make protect-branches  - Apply branch protection rules (requires gh CLI)"
	@echo "  make check-forbidden   - Run grep-guards against regression patterns (S-48)"
	@echo "  make ci                - Run all CI checks locally (lint + format + typecheck + check-forbidden)"
	@echo ""

# Installation
install:
	poetry install --no-interaction

update:
	poetry update --no-interaction

# Run bot
run:
	poetry run python -m src.bot.main

# Testing
test:
	poetry run pytest tests/ -v --tb=short

test-cov:
	poetry run pytest tests/ -v --tb=short --cov=src --cov-report=html

# Linting and formatting
lint:
	poetry run ruff check src/ tests/

format:
	poetry run ruff format src/ tests/

lint-fix:
	poetry run ruff check src/ tests/ --fix

# Type checking
typecheck:
	poetry run mypy src/

# Grep-guards: regression patterns banned by S-48
check-forbidden:
	@bash scripts/check_forbidden_patterns.sh

# CI checks (run all checks locally before pushing)
ci: lint format typecheck check-forbidden
	@echo ""
	@echo "✓ All CI checks passed locally!"
	@echo ""

# Database migrations
migrate:
	poetry run alembic upgrade head

migrate-revision:
	poetry run alembic revision --autogenerate -m "$(message)"

migrate-downgrade:
	poetry run alembic downgrade -1

# Shell with DB session
shell:
	poetry run python -c "\
		from src.db.session import AsyncSessionLocal; \
		from src.db.base import DeclarativeBase; \
		import asyncio; \
		asyncio.run(__import__('code').interact(local={'session': AsyncSessionLocal}))"

# Docker commands
docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

docker-ps:
	docker compose ps

docker-restart:
	docker compose restart

# Branch Protection Rules
# Requires: gh CLI installed and authenticated (gh auth login)
# Token must have admin:repo or admin permissions
protect-branches:
	@echo "Applying branch protection rules..."
	@chmod +x scripts/apply_branch_protection.sh
	@./scripts/apply_branch_protection.sh

# Clean
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete
	rm -rf dist/ build/ *.egg-info/

# Pre-commit
pre-commit-install:
	pre-commit install

pre-commit-run:
	pre-commit run --all-files

# Full pre-commit check (lint + format + typecheck + tests)
check:
	@echo "Running full pre-commit checks..."
	@echo ""
	poetry run ruff check src/ tests/
	poetry run ruff format --check src/ tests/
	poetry run mypy src/
	poetry run pytest tests/ --tb=short -v
	@echo ""
	@echo "✓ All checks passed!"

# Local CI gate — equivalent to GH CI when GH Actions unavailable (BL-017).
# See CONTRIBUTING.md for baseline tolerance (BL-007 ruff, BL-019 test debt).
ci-local:
	@echo "=== ci-local: Forbidden patterns ==="
	@bash scripts/check_forbidden_patterns.sh
	@echo "=== ci-local: Lint ==="
	poetry run ruff check src/ tests/
	@echo "=== ci-local: Format check ==="
	poetry run ruff format --check src/ tests/
	@echo "=== ci-local: Type check ==="
	poetry run mypy src/
	@echo "=== ci-local: Tests (excluding e2e_api due to docker-compose.test.yml requirement) ==="
	poetry run pytest tests/ \
		--ignore=tests/e2e_api \
		--ignore=tests/unit/test_main_menu.py \
		--no-cov \
		--tb=short
	@echo "=== ci-local: PASSED ==="

# ══════════════════════════════════════════════════════════════
# Web Portal (S-27)
# ══════════════════════════════════════════════════════════════

build-portal:
	@echo "Building web portal..."
	cd web_portal && npm ci && npm run build
	@echo "✓ Web portal built in web_portal/dist/"

deploy-portal: build-portal
	@echo "Deploying web portal to server..."
	@echo "  1. git pull on server"
	@echo "  2. cd web_portal && npm ci && npm run build"
	@echo "  3. docker compose up -d --no-deps nginx"
	@echo ""
	@echo "Run on server: cd /opt/market-telegram-bot && git pull && make build-portal && docker compose up -d --no-deps nginx"

portal-dev:
	cd web_portal && npm run dev

portal-preview:
	cd web_portal && npm run preview

# ══════════════════════════════════════════════════════════════
# E2E Tests — Playwright in Docker (isolated runtime)
# ══════════════════════════════════════════════════════════════

E2E_COMPOSE := docker compose -p e2e -f docker-compose.test.yml --env-file .env.test

# One-shot: build, seed, run API contract + UI smoke back-to-back in the same
# stack, tear down. Exits non-zero if either suite fails.
test-e2e:
	$(E2E_COMPOSE) up --build -d postgres-test redis-test seed-test api-test nginx-test ; \
	api_status=0 ; ui_status=0 ; \
	$(E2E_COMPOSE) run --rm api-contract || api_status=$$? ; \
	$(E2E_COMPOSE) run --rm playwright || ui_status=$$? ; \
	$(E2E_COMPOSE) down -v --remove-orphans ; \
	if [ $$api_status -ne 0 ] || [ $$ui_status -ne 0 ]; then \
		echo "API contract exit=$$api_status, UI exit=$$ui_status" ; \
		exit 1 ; \
	fi

# API contract tests only — pytest inside the test stack
test-e2e-api:
	$(E2E_COMPOSE) up --build -d postgres-test redis-test seed-test api-test nginx-test ; \
	$(E2E_COMPOSE) run --rm api-contract ; \
	status=$$? ; \
	$(E2E_COMPOSE) down -v --remove-orphans ; \
	exit $$status

# Keep test stack running (for local iteration — run `npx playwright test` manually)
test-e2e-up:
	$(E2E_COMPOSE) up --build -d postgres-test redis-test seed-test api-test nginx-test

test-e2e-down:
	$(E2E_COMPOSE) down -v --remove-orphans

test-e2e-logs:
	$(E2E_COMPOSE) logs -f

# Refresh visual regression baselines (commit resulting PNGs to git).
# Use after an intentional UI change.
test-e2e-visual-update:
	$(E2E_COMPOSE) up --build -d postgres-test redis-test seed-test api-test nginx-test ; \
	$(E2E_COMPOSE) run --rm playwright npx playwright test visual.spec.ts --update-snapshots ; \
	status=$$? ; \
	$(E2E_COMPOSE) down -v --remove-orphans ; \
	exit $$status
