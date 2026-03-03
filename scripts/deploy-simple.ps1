# Market Bot — Deployment Script (PowerShell)
# Использование: .\scripts\deploy-to-server.ps1

$SERVER_SSH = "zerodolg-server"
$SERVER_PATH = "/opt/market-telegram-bot"
$LOCAL_BRANCH = "developer2/belin"

Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║     Market Bot — Production Deployment                    ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

Write-Host "ℹ Деплой на сервер $SERVER_SSH`:$SERVER_PATH..." -ForegroundColor Cyan
Write-Host ""

# 1. Git pull
Write-Host "✓ Git pull..." -ForegroundColor Green
ssh $SERVER_SSH "cd $SERVER_PATH && git fetch origin $LOCAL_BRANCH && git checkout $LOCAL_BRANCH && git reset --hard origin/$LOCAL_BRANCH"

# 2. Docker pull
Write-Host "✓ Docker pull..." -ForegroundColor Green
ssh $SERVER_SSH "cd $SERVER_PATH && docker compose pull"

# 3. Миграции
Write-Host "✓ Миграции..." -ForegroundColor Green
ssh $SERVER_SSH "cd $SERVER_PATH && docker compose run --rm bot poetry run alembic upgrade head"

# 4. Обновление сервисов
Write-Host "✓ Обновление сервисов..." -ForegroundColor Green
ssh $SERVER_SSH "cd $SERVER_PATH && docker compose up -d --no-deps bot api worker celery_beat"

# 5. Ожидание
Write-Host "ℹ Ожидание запуска (15 сек)..." -ForegroundColor Cyan
Start-Sleep -Seconds 15

# 6. Проверка
Write-Host "✓ Проверка сервисов..." -ForegroundColor Green
ssh $SERVER_SSH "cd $SERVER_PATH && docker compose ps"

# 7. Очистка
Write-Host "✓ Очистка..." -ForegroundColor Green
ssh $SERVER_SSH "cd $SERVER_PATH && docker image prune -f"

Write-Host ""
Write-Host "✅ Деплой завершён успешно!" -ForegroundColor Green
Write-Host ""
Write-Host "ℹ Мониторинг: ssh $SERVER_SSH 'cd $SERVER_PATH && docker compose logs -f'" -ForegroundColor Cyan
