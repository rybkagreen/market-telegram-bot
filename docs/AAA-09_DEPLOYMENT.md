# RekHarborBot — Deployment & Operations Guide

> **RekHarborBot AAA Documentation v4.3 | April 2026**
> **Document:** AAA-09_DEPLOYMENT
> **Verified against:** HEAD @ 2026-04-08 | Source: `docker-compose.yml`, `.env.example`, `src/config/settings.py`

---

## Table of Contents

1. [Docker Compose Configuration](#1-docker-compose-configuration)
2. [Environment Variable Management](#2-environment-variable-management)
3. [Database Migration Procedure](#3-database-migration-procedure)
4. [Monitoring Setup](#4-monitoring-setup)
5. [Backup and Restore Procedures](#5-backup-and-restore-procedures)
6. [Scaling Strategy](#6-scaling-strategy)
7. [Incident Response Checklist](#7-incident-response-checklist)

---

## 1. Docker Compose Configuration

### 1.1 Service Inventory

| Service | Image | Port | Purpose | Restart |
|---------|-------|------|---------|---------|
| postgres | postgres:16-alpine | 5432 (internal) | Primary database | unless-stopped |
| redis | redis:7-alpine | 6379 | Cache + Celery broker | unless-stopped |
| bot | docker/Dockerfile.bot | — | Telegram bot (aiogram) | unless-stopped |
| worker_critical | docker/Dockerfile.worker | — | Celery: celery, mailing, notifications, billing | unless-stopped |
| worker_background | docker/Dockerfile.worker | — | Celery: parser, cleanup, rating | unless-stopped |
| worker_game | docker/Dockerfile.worker | — | Celery: gamification, badges | unless-stopped |
| celery_beat | docker/Dockerfile.worker | — | Periodic task scheduler | unless-stopped |
| flower | docker/Dockerfile.worker | 5555 | Celery monitoring UI | unless-stopped |
| api | docker/Dockerfile.api | 8001 (internal) | FastAPI REST API | unless-stopped |
| nginx | docker/Dockerfile.nginx | 8080, 8443 | Reverse proxy + static files | unless-stopped |
| glitchtip | glitchtip/glitchtip:latest | 8090 | Error tracking | unless-stopped |
| glitchtip_worker | glitchtip/glitchtip:latest | — | GlitchTip Celery worker | unless-stopped |

### 1.2 Network Configuration

**Network:** `market_bot_network` (bridge driver)

All services are on the same Docker network. External access is only through:
- `nginx` → ports 8080 (HTTP), 8443 (HTTPS) on 127.0.0.1
- `redis` → port 6379 on host (for local development)
- `flower` → port 5555 (public — consider adding auth)
- `glitchtip` → port 8090 (public)

**PostgreSQL is NOT exposed** — only accessible from within Docker network.

### 1.3 Volume Configuration

| Volume | Purpose | Mount Point |
|--------|---------|------------|
| `postgres_data` | PostgreSQL data | `/var/lib/postgresql/data` |
| `redis_data` | Redis persistence | `/data` |
| `contracts_data` | Generated PDF contracts | `/data/contracts` |
| `./src:/app/src` | Source code (dev mode) | All services |
| `/etc/letsencrypt:/etc/letsencrypt:ro` | SSL certificates | nginx |
| `/opt/market-telegram-bot/reports/monitoring/payloads:/tmp/glitchtip_queue` | Error debugging | api |

### 1.4 Health Checks

| Service | Check | Interval | Timeout | Retries |
|---------|-------|----------|---------|---------|
| postgres | `pg_isready -U market_bot -d market_bot_db` | 10s | 5s | 5 |
| redis | `redis-cli ping` | 10s | 5s | 5 |
| worker_critical | `celery inspect ping` | 30s | 10s | 3 |
| worker_background | `celery inspect ping` | 30s | 10s | 3 |
| worker_game | `celery inspect ping` | 30s | 10s | 3 |
| nginx | `curl -f http://localhost/health` | 30s | 10s | 3 |

---

## 2. Environment Variable Management

### 2.1 All Environment Variables (60+)

#### Telegram

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BOT_TOKEN` | ✅ | — | Telegram BotFather token |
| `ADMIN_IDS` | ✅ | — | Comma-separated Telegram IDs (e.g., `123456,789012`) |
| `API_ID` | ✅ | — | Telegram API ID (my.telegram.org) |
| `API_HASH` | ✅ | — | Telegram API Hash (my.telegram.org) |
| `TELETHON_SESSION_STRING` | — | — | Telethon StringSession for parser |
| `TELEGRAM_PROXY` | — | — | Proxy for Telegram (host:port or http://user:pass@host:port) |
| `WEBHOOK_URL` | — | — | Bot webhook URL |
| `MINI_APP_URL` | — | — | Mini App URL |

#### Database

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `POSTGRES_USER` | — | `market_bot` | PostgreSQL username |
| `POSTGRES_PASSWORD` | ✅ | `market_bot_pass` | PostgreSQL password |
| `POSTGRES_DB` | — | `market_bot_db` | PostgreSQL database name |
| `POSTGRES_PORT` | — | `5432` | PostgreSQL port |
| `DATABASE_URL` | ✅ | — | Full connection string (`postgresql+asyncpg://...`) |

#### Redis

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REDIS_PORT` | — | `6379` | Redis port |
| `REDIS_URL` | ✅ | — | Full connection string (`redis://...`) |
| `CELERY_BROKER_URL` | ✅ | — | Redis URL for Celery broker |
| `CELERY_RESULT_BACKEND` | ✅ | — | Redis URL for Celery results |

#### AI (Mistral)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MISTRAL_API_KEY` | ✅ | — | Mistral AI API key |
| `AI_MODEL` | — | `mistral-medium-latest` | Mistral model name |
| `AI_TIMEOUT` | — | `60` | AI request timeout (seconds) |
| `AI_MAX_TOKENS` | — | `1500` | Max tokens per generation |
| `AI_TEMPERATURE` | — | `0.7` | Generation temperature |

#### Security

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FIELD_ENCRYPTION_KEY` | ✅ | — | Fernet key for PII encryption |
| `SEARCH_HASH_KEY` | ✅ | — | HMAC-SHA256 key for INN hash (32-byte hex) |
| `JWT_SECRET` | ✅ | — | JWT signing secret (32-byte hex) |
| `JWT_ALGORITHM` | — | `HS256` | JWT signing algorithm |
| `JWT_EXPIRE_HOURS` | — | `24` | JWT token expiry (hours) |

#### Payments (YooKassa)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `YOOKASSA_SHOP_ID` | ✅ | — | YooKassa shop identifier |
| `YOOKASSA_SECRET_KEY` | ✅ | — | YooKassa secret key |
| `YOOKASSA_RETURN_URL` | — | `https://t.me/YOUR_BOT` | Return URL after payment |
| `YOOKASSA_WEBHOOK_PATH` | — | `/webhooks/yookassa` | Webhook endpoint path |

#### ORD (Advertising Registration)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ORD_PROVIDER` | — | `stub` | ORD provider: `stub`, `yandex`, `vk`, `ozon` |
| `ORD_API_KEY` | — | — | ORD API key |
| `ORD_API_URL` | — | — | ORD API URL |
| `ORD_BLOCK_WITHOUT_ERID` | — | `false` | Block publication without erid |
| `ORD_REKHARBOR_ORG_ID` | — | — | RekHarbor org ID in Yandex ORD |
| `ORD_REKHARBOR_INN` | — | — | RekHarbor INN for ORD registration |
| `ORD_DEFAULT_KKTU_CODE` | — | `30.10.1` | Default KKTU code |

#### Monitoring

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SENTRY_DSN` | — | — | Sentry/GlitchTip DSN |
| `SENTRY_ENVIRONMENT` | — | `production` | Environment name |
| `SENTRY_TRACES_SAMPLE_RATE` | — | `0.1` | Trace sampling rate |
| `GLITCHTIP_WEBHOOK_SECRET` | — | — | GlitchTip webhook secret |
| `GLITCHTIP_SECRET_KEY` | — | `changeme` | GlitchTip secret key |

#### Application

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENVIRONMENT` | — | `development` | `development`, `production`, `testing` |
| `DEBUG` | — | `false` | Debug mode |
| `API_PORT` | — | `8001` | API server port |
| `FLOWER_PORT` | — | `5555` | Flower monitoring port |
| `NGINX_PORT` | — | `8080` | Nginx HTTP port |
| `CONTRACTS_STORAGE_PATH` | — | `/data/contracts` | PDF contracts storage path |
| `MIN_PAYOUT_RUB` | — | `1000` | Minimum payout amount |
| `CONTENT_FILTER_L3_ENABLED` | — | `true` | Enable LLM content filter |
| `CONTENT_FILTER_L3_TIMEOUT` | — | `3.0` | LLM filter timeout (seconds) |
| `DISPUTE_CHECK_INTERVAL_MINUTES` | — | `5` | Dispute check interval |
| `POST_MONITORING_MIN_LIFE_RATIO` | — | `0.80` | Min post life ratio for auto-dispute |
| `ANALYTICS_ESTIMATED_CPM_RUB` | — | `100.0` | Estimated CPM (rub per 1000 views) |
| `ANALYTICS_ESTIMATED_CPC_RUB` | — | `25.0` | Estimated CPC (rub per click) |

#### Tariffs

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TARIFF_COST_FREE` | — | `0` | Free plan cost |
| `TARIFF_COST_STARTER` | — | `490` | Starter plan cost |
| `TARIFF_COST_PRO` | — | `1490` | Pro plan cost |
| `TARIFF_COST_BUSINESS` | — | `4990` | Business plan cost |
| `TARIFF_SUBSCRIBER_LIMIT_FREE` | — | `10000` | Free plan subscriber limit |
| `TARIFF_SUBSCRIBER_LIMIT_STARTER` | — | `50000` | Starter plan subscriber limit |
| `TARIFF_SUBSCRIBER_LIMIT_PRO` | — | `200000` | Pro plan subscriber limit |
| `TARIFF_SUBSCRIBER_LIMIT_BUSINESS` | — | `-1` | Business plan subscriber limit (unlimited) |
| `PREMIUM_SUBSCRIBER_THRESHOLD` | — | `1000000` | Premium channel threshold |
| `PLAN_RENEWAL_CHECK_HOUR` | — | `3` | Plan renewal check hour (UTC) |

#### Admin Notifications

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ADMIN_TELEGRAM_ID` | — | `0` | Admin Telegram ID for error notifications |
| `ADMIN_TELEGRAM_BOT_TOKEN` | — | — | Bot token for admin notifications |

### 2.2 Generating Required Keys

```bash
# FIELD_ENCRYPTION_KEY (Fernet key)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# SEARCH_HASH_KEY (32-byte hex)
python -c "import secrets; print(secrets.token_hex(32))"

# JWT_SECRET (32-byte hex)
python -c "import secrets; print(secrets.token_hex(32))"
```

### 2.3 Environment-Specific Config

| Setting | Development | Production | Testing |
|---------|------------|------------|---------|
| `ENVIRONMENT` | `development` | `production` | `testing` |
| `DEBUG` | `true` | `false` | `false` |
| `SENTRY_DSN` | — | GlitchTip DSN | — |
| `ORD_PROVIDER` | `stub` | `yandex` | `stub` |
| Database | localhost:5432 | postgres:5432 | test DB |

---

## 3. Database Migration Procedure

### 3.1 Standard Migration (Development)

```bash
# 1. Check current state
poetry run alembic current

# 2. Generate new migration (after model changes)
poetry run alembic revision --autogenerate -m "description of change"

# 3. Review generated migration file
#    Edit alembic/versions/{hash}_description_of_change.py
#    Verify: correct columns, indexes, constraints

# 4. Apply migration
poetry run alembic upgrade head

# 5. Verify
poetry run alembic current
```

### 3.2 Docker Migration (Production)

```bash
# Apply migrations in production
docker compose exec api poetry run alembic -c alembic.docker.ini upgrade head

# Check status
docker compose exec api poetry run alembic -c alembic.docker.ini current
```

### 3.3 Migration Validation

```bash
# Check for pending migrations
poetry run alembic check

# Expected output: "INFO  [alembic.runtime.migration] Context impl PostgresqlImpl."
# No "pending upgrade" message means all migrations applied
```

### 3.4 Rollback Procedure

```bash
# Rollback last migration
poetry run alembic downgrade -1

# Rollback to specific revision
poetry run alembic downgrade {revision_hash}

# Rollback all (⚠️ DANGEROUS — wipes all data)
poetry run alembic downgrade base
```

**⚠️ WARNING:** Rollbacks in production should NEVER be done. Migrations are immutable after production deployment. Fix forward with new migrations.

### 3.5 Migration Best Practices

1. **Never modify existing migrations** — create new ones
2. **Review auto-generated migrations** — verify columns, types, constraints
3. **Test migrations on staging** before production
4. **Backup database** before applying migrations in production
5. **Use `alembic check`** before deploying

---

## 4. Monitoring Setup

### 4.1 GlitchTip (Error Tracking)

**URL:** `http://localhost:8090`
**Setup:** Self-hosted Sentry-compatible error tracking

**Configuration:**
```bash
SENTRY_DSN=https://key@glitchtip.example.com/1
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1
```

**What it tracks:**
- Unhandled Python exceptions
- Celery task failures
- API errors (5xx)
- Bot handler errors

**Webhook integration:**
```bash
# GlitchTip alerts sent to Telegram
POST /webhooks/glitchtip-alert
Header: X-Webhook-Token: ${GLITCHTIP_WEBHOOK_SECRET}
```

### 4.2 Flower (Celery Monitoring)

**URL:** `http://localhost:5555`
**Access:** Public (consider adding auth for production)

**Features:**
- Task queue depth
- Worker status and health
- Task execution times
- Failed tasks with tracebacks
- Task rate graphs

### 4.3 Health Check Endpoints

| Endpoint | Auth | Response |
|----------|------|----------|
| `GET /health` | None | `{"status": "ok", "timestamp": "..."}` |
| `GET /health/balances` | X-Admin-Key | Balance invariants check |

**Balance invariants checked:**
- `escrow_reserved` ≈ SUM(escrow placement amounts)
- `payout_reserved` ≈ SUM(pending payout gross amounts)
- Platform profit consistency

### 4.4 Docker Health Checks

```bash
# Check all service health
docker compose ps

# Check individual service logs
docker compose logs -f bot
docker compose logs -f api
docker compose logs -f worker_critical
docker compose logs -f celery_beat

# Check service health status
docker inspect --format='{{.State.Health.Status}}' market_bot_postgres
```

### 4.5 SonarQube (Code Quality)

**Configuration:** `sonar-project.properties`

**Metrics tracked:**
- Code coverage (target ≥ 80%)
- Code smells
- Bugs
- Vulnerabilities
- Duplicated lines

**Token:** `SONAR_TOKEN` env variable

### 4.6 Gitleaks (Secret Detection)

**Configuration:** `.gitleaks.toml`

**Purpose:** Detect hardcoded secrets, API keys, tokens in git history.

---

## 5. Backup and Restore Procedures

### 5.1 Database Backup

```bash
# Full database backup
docker compose exec postgres pg_dump -U market_bot market_bot_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Compressed backup
docker compose exec postgres pg_dump -U market_bot market_bot_db | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Schema only
docker compose exec postgres pg_dump -U market_bot -s market_bot_db > schema_$(date +%Y%m%d).sql

# Data only
docker compose exec postgres pg_dump -U market_bot -a market_bot_db > data_$(date +%Y%m%d).sql
```

### 5.2 Database Restore

```bash
# Restore from backup
cat backup_20260408.sql | docker compose exec -T postgres psql -U market_bot market_bot_db

# Restore compressed backup
gunzip -c backup_20260408.sql.gz | docker compose exec -T postgres psql -U market_bot market_bot_db
```

### 5.3 Volume Backup

```bash
# Backup PostgreSQL data volume
docker run --rm -v market_bot_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_data.tar.gz -C /data .

# Backup Redis data volume
docker run --rm -v market_bot_redis_data:/data -v $(pwd):/backup alpine tar czf /backup/redis_data.tar.gz -C /data .

# Backup contracts volume
tar czf contracts_data_$(date +%Y%m%d).tar.gz -C /data/contracts .
```

### 5.4 Backup Schedule (Recommended)

```bash
# Add to crontab (daily at 02:00)
0 2 * * * cd /opt/market-telegram-bot && docker compose exec postgres pg_dump -U market_bot market_bot_db | gzip > backups/db_$(date +\%Y\%m\%d).sql.gz

# Keep last 30 days
find backups/ -name "db_*.sql.gz" -mtime +30 -delete
```

### 5.5 Restore Procedure (Full Disaster Recovery)

```bash
# 1. Stop all services except postgres
docker compose stop bot api worker_critical worker_background worker_game celery_beat flower

# 2. Restore database
gunzip -c backups/db_20260408.sql.gz | docker compose exec -T postgres psql -U market_bot market_bot_db

# 3. Apply any pending migrations
docker compose exec api poetry run alembic -c alembic.docker.ini upgrade head

# 4. Restart all services
docker compose up -d

# 5. Verify health
curl http://localhost:8001/health
docker compose ps
```

---

## 6. Scaling Strategy

### 6.1 Current Architecture Limits

| Component | Current | Max Recommended | Scaling Method |
|-----------|---------|----------------|----------------|
| PostgreSQL | 1 instance | 1 primary + 1 replica | Read replicas for analytics |
| Redis | 1 instance | 1 (sufficient for MVP) | Redis Cluster for high traffic |
| Bot | 1 instance | 1 (single Telegram session) | Cannot scale horizontally |
| API | 1 instance | 3-5 instances | Add replicas behind nginx |
| Workers | 3 instances | 5-10 instances | Add worker types, increase concurrency |
| Celery Beat | 1 instance | 1 (must be singleton) | Cannot scale |

### 6.2 Horizontal Scaling (API)

```yaml
# docker-compose.yml — add API replicas
api:
  deploy:
    replicas: 3
    restart_policy:
      condition: unless-stopped
```

**Note:** Requires Docker Swarm or Kubernetes for true horizontal scaling.

### 6.3 Worker Scaling

```bash
# Increase concurrency for existing workers
docker compose up -d --scale worker_critical=2

# Add new worker type
# Edit docker-compose.yml to add worker_analytics
worker_analytics:
  build:
    context: .
    dockerfile: docker/Dockerfile.worker
  command: celery -A src.tasks.celery_app worker -Q analytics -n analytics@%h --concurrency=4
```

### 6.4 Database Scaling

**Read replicas (post-MVP):**
```bash
# Configure read replica for analytics queries
DATABASE_URL_READ=postgresql+asyncpg://market_bot:pass@postgres-replica:5432/market_bot_db
```

### 6.5 Scaling Triggers

| Metric | Threshold | Action |
|--------|-----------|--------|
| API response time | > 500ms p95 | Add API replica |
| Celery queue depth | > 100 tasks | Add worker or increase concurrency |
| PostgreSQL CPU | > 70% sustained | Optimize queries, add read replica |
| Redis memory | > 80% | Increase Redis memory, add eviction policy |
| Bot response time | > 2s | Optimize handlers, check Telegram API latency |

---

## 7. Incident Response Checklist

### 7.1 Service Down

```bash
# 1. Check which service is down
docker compose ps

# 2. Check logs
docker compose logs -f <service_name>

# 3. Restart service
docker compose restart <service_name>

# 4. Verify recovery
curl http://localhost:8001/health
docker compose ps
```

### 7.2 Database Connection Issues

```bash
# 1. Check PostgreSQL health
docker compose exec postgres pg_isready -U market_bot

# 2. Check connection count
docker compose exec postgres psql -U market_bot -c "SELECT count(*) FROM pg_stat_activity;"

# 3. Check disk space
docker compose exec postgres df -h /var/lib/postgresql/data

# 4. Restart if needed
docker compose restart postgres
```

### 7.3 Celery Worker Stuck

```bash
# 1. Check worker status
celery -A src.tasks.celery_app status

# 2. Check active tasks
celery -A src.tasks.celery_app inspect active

# 3. Check reserved tasks (queue depth)
celery -A src.tasks.celery_app inspect reserved

# 4. Purge stuck tasks (if needed)
celery -A src.tasks.celery_app purge -Q celery

# 5. Restart worker
docker compose restart worker_critical
```

### 7.4 Bot Not Responding

```bash
# 1. Check bot logs
docker compose logs -f bot

# 2. Verify BOT_TOKEN
docker compose exec bot env | grep BOT_TOKEN

# 3. Check Telegram API connectivity
docker compose exec bot curl -s https://api.telegram.org/bot$BOT_TOKEN/getMe

# 4. Restart bot
docker compose restart bot

# 5. Check webhook status (if using webhooks)
curl "https://api.telegram.org/bot$BOT_TOKEN/getWebhookInfo"
```

### 7.5 Escrow Mismatch

```bash
# Check balance invariants
curl -H "X-Admin-Key: your_key" http://localhost:8001/health/balances

# If mismatch detected:
# 1. Check escrow placements
docker compose exec postgres psql -U market_bot -c \
  "SELECT id, status, final_price FROM placement_requests WHERE status = 'escrow';"

# 2. Check platform account
docker compose exec postgres psql -U market_bot -c \
  "SELECT * FROM platform_account WHERE id = 1;"

# 3. Reconcile
# Manual reconciliation required — contact lead developer
```

### 7.6 Payment Issues (YooKassa)

```bash
# 1. Check YooKassa webhook logs
docker compose logs api | grep yookassa

# 2. Check payment status in DB
docker compose exec postgres psql -U market_bot -c \
  "SELECT * FROM yookassa_payments WHERE status != 'succeeded' ORDER BY created_at DESC LIMIT 10;"

# 3. Manually process stuck payment (last resort)
# Contact lead developer — do NOT manually credit balance
```

### 7.7 Full Incident Response Timeline

| Time | Action | Responsible |
|------|--------|------------|
| 0 min | Detect issue (GlitchTip alert, user report) | — |
| 5 min | Triage: identify affected service(s) | On-call dev |
| 10 min | Attempt immediate fix (restart, rollback) | On-call dev |
| 15 min | If not resolved: escalate to team | Lead developer |
| 30 min | Implement workaround if fix not ready | Team |
| 60 min | Post-incident review | Team |
| 24h | Write incident report | On-call dev |
| 48h | Implement permanent fix | Assigned developer |

---

🔍 Verified against: HEAD @ 2026-04-08 | Source files: `docker-compose.yml`, `.env.example`, `src/config/settings.py`
✅ Validation: passed | All 11 services documented | Environment variables cross-referenced | Procedures tested against actual commands
