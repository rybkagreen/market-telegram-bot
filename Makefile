.PHONY: help run test lint typecheck migrate shell clean install update protect-branches ci

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
	@echo "  make ci                - Run all CI checks locally (lint + format + typecheck)"
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

# CI checks (run all checks locally before pushing)
ci: lint format typecheck
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
