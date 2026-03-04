# Market Bot — Деплой с локальной машины на сервер (PowerShell версия)
# Использование: .\scripts\deploy-from-local.ps1

param(
    [switch]$AutoConfirm
)

$SERVER_SSH = "zerodolg-server"
$SERVER_PATH = "/opt/market-telegram-bot"
$LOCAL_BRANCH = "main"
$DEPLOY_LOG = "C:\temp\deploy-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"

# Сервисы для пересборки
$SERVICES_TO_REBUILD = @("bot", "api", "worker", "celery_beat", "nginx", "flower")
$CRITICAL_SERVICES = @("bot", "api", "nginx")

# Функции логирования
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logLine = "[$timestamp] [$Level] $Message"
    Add-Content -Path $DEPLOY_LOG -Value $logLine
    
    switch ($Level) {
        "OK" { Write-Host "✓ $Message" -ForegroundColor Green }
        "WARN" { Write-Host "⚠ $Message" -ForegroundColor Yellow }
        "ERROR" { Write-Host "✗ $Message" -ForegroundColor Red }
        "INFO" { Write-Host "ℹ $Message" -ForegroundColor Cyan }
        default { Write-Host $Message }
    }
}

# Проверка SSH
function Test-SSHConnection {
    Write-Log "Проверка SSH-соединения..." "INFO"
    try {
        $null = ssh -o ConnectTimeout=10 -o BatchMode=yes $SERVER_SSH "exit" 2>$null
        Write-Log "SSH-соединение OK" "OK"
        return $true
    } catch {
        Write-Log "Не удалось подключиться к серверу!" "ERROR"
        return $false
    }
}

# Бэкап
function Invoke-Backup {
    Write-Log "Создание бэкапа на сервере..." "INFO"
    ssh $SERVER_SSH "
    cd $SERVER_PATH &&
    [ -f .env ] && cp .env .env.backup.\$(date +%Y%m%d_%H%M%S) &&
    [ -f docker-compose.yml ] && cp docker-compose.yml docker-compose.yml.backup.\$(date +%Y%m%d_%H%M%S) &&
    echo 'Бэкап создан'
    " 2>$null
}

# Откат
function Invoke-Rollback {
    Write-Log "Выполняется откат..." "WARN"
    ssh $SERVER_SSH "
    cd $SERVER_PATH &&
    docker compose up -d 2>/dev/null || echo 'Откат не выполнен'
    "
}

# Ожидание сервиса
function Wait-ForService {
    param([string]$Service, [int]$MaxAttempts = 30)
    Write-Log "Ожидание запуска $Service..." "INFO"
    
    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        $result = ssh $SERVER_SSH "cd $SERVER_PATH && docker compose ps $Service 2>/dev/null | Select-String 'Up'" 2>$null
        if ($result) {
            Write-Log "$Service: запущен (попытка $attempt)" "OK"
            return $true
        }
        Start-Sleep -Seconds 2
    }
    
    Write-Log "$Service: не запустился!" "ERROR"
    return $false
}

# Health check
function Test-HealthCheck {
    Write-Log "Health check API..." "INFO"
    
    for ($attempt = 1; $attempt -le 10; $attempt++) {
        $result = ssh $SERVER_SSH "curl -sf http://localhost:8001/health" 2>$null
        if ($result) {
            Write-Log "API health check: OK" "OK"
            return $true
        }
        Start-Sleep -Seconds 2
        Write-Log "Ожидание API... (попытка $attempt/10)" "INFO"
    }
    
    Write-Log "API health check: FAILED" "WARN"
    return $false
}

# Основная функция деплоя
function Invoke-Deploy {
    Write-Log "Начало деплоя → ${SERVER_SSH}:${SERVER_PATH} [ветка: $LOCAL_BRANCH]" "INFO"
    
    # 1. SSH проверка
    if (-not (Test-SSHConnection)) {
        Write-Log "Деплой отменён — SSH недоступен" "ERROR"
        return $false
    }
    
    # 2. Бэкап
    Invoke-Backup
    
    # 3. Синхронизация файлов
    Write-Log "Синхронизация файлов с сервером..." "INFO"
    Write-Log "Используется rsync через SSH..." "INFO"
    
    $exclude = @(".git", ".gitignore", "__pycache__", "*.pyc", ".env", ".venv", "venv", "*.log", ".pytest_cache", ".mypy_cache", "node_modules")
    $rsyncArgs = @("-avz", "--delete", "-e", "ssh -o ConnectTimeout=10")
    
    foreach ($exc in $exclude) {
        $rsyncArgs += "--exclude='$exc'"
    }
    
    $rsyncArgs += ".\", "$SERVER_SSH`:$SERVER_PATH/\""
    
    try {
        & rsync @rsyncArgs 2>&1 | Out-File -Append $DEPLOY_LOG
        Write-Log "Файлы синхронизированы" "OK"
    } catch {
        Write-Log "rsync не найден или ошибка синхронизации!" "ERROR"
        Write-Log "Установите rsync: winget install GnuWin32.Rsync" "WARN"
        Invoke-Rollback
        return $false
    }
    
    # 4. Проверка .env
    Write-Log "1. Проверка .env..." "INFO"
    $envCheck = ssh $SERVER_SSH "[ -f $SERVER_PATH/.env ]" 2>$null
    if (-not $envCheck) {
        Write-Log ".env файл не найден на сервере!" "ERROR"
        Invoke-Rollback
        return $false
    }
    
    # 5. Пересборка Docker образов
    Write-Log "2. Пересборка Docker образов (без кэша)..." "INFO"
    Write-Log "Это может занять 5-15 минут..." "WARN"
    
    $buildResult = ssh $SERVER_SSH "
    cd $SERVER_PATH &&
    docker compose build --no-cache --pull $($SERVICES_TO_REBUILD -join ' ')
    " 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Write-Log "Docker build failed!" "ERROR"
        Invoke-Rollback
        return $false
    }
    
    # 6. Применение миграций
    Write-Log "3. Применение миграций..." "INFO"
    $migrateResult = ssh $SERVER_SSH "
    cd $SERVER_PATH &&
    docker compose run --rm bot poetry run alembic upgrade head
    " 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Write-Log "Миграции failed!" "ERROR"
        Invoke-Rollback
        return $false
    }
    
    # 7. Остановка старых контейнеров
    Write-Log "4. Остановка старых контейнеров..." "INFO"
    ssh $SERVER_SSH "cd $SERVER_PATH && docker compose stop $($SERVICES_TO_REBUILD -join ' ')" 2>$null
    
    # 8. Запуск обновлённых сервисов
    Write-Log "5. Запуск обновлённых сервисов..." "INFO"
    ssh $SERVER_SSH "
    cd $SERVER_PATH &&
    docker compose up -d --no-deps $($SERVICES_TO_REBUILD -join ' ')
    "
    
    # 9. Ожидание критических сервисов
    Write-Log "6. Проверка запуска критических сервисов..." "INFO"
    foreach ($service in $CRITICAL_SERVICES) {
        if (-not (Wait-ForService $service)) {
            Write-Log "Критический сервис $service не запустился!" "ERROR"
            Invoke-Rollback
            return $false
        }
    }
    
    # 10. Health check
    Test-HealthCheck
    
    # 11. Проверка всех контейнеров
    Write-Log "7. Статус всех контейнеров..." "INFO"
    ssh $SERVER_SSH "cd $SERVER_PATH && docker compose ps"
    
    # 12. Очистка
    Write-Log "8. Очистка старых образов..." "INFO"
    ssh $SERVER_SSH "cd $SERVER_PATH && docker image prune -f"
    
    Write-Log "Деплой завершён успешно!" "OK"
    return $true
}

# ══════════════════════════════════════════════════════════════
# ОСНОВНОЙ СЦЕНАРИЙ
# ══════════════════════════════════════════════════════════════

Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║     Market Bot — Деплой с локальной машина (PowerShell)   ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Проверка текущей директории
if (-not (Test-Path "docker-compose.yml")) {
    Write-Log "docker-compose.yml не найден! Запускайте из корня проекта" "ERROR"
    exit 1
}

Write-Log "Внимание! Будет выполнен деплой с локального кода:" "WARN"
Write-Host "  Сервер: $SERVER_SSH"
Write-Host "  Путь: $SERVER_PATH"
Write-Host "  Сервисы: $($SERVICES_TO_REBUILD -join ', ')"
Write-Host "  Режим: BUILD --no-cache (без кэша)"
Write-Host "  Лог: $DEPLOY_LOG"
Write-Host ""
Write-Log "⚠ Пересборка без кэша может занять 5-15 минут!" "WARN"
Write-Host ""

if (-not $AutoConfirm) {
    $confirm = Read-Host "Продолжить деплой? (y/n)"
    if ($confirm -ne 'y' -and $confirm -ne 'Y') {
        Write-Log "Деплой отменён" "WARN"
        exit 0
    }
}

# Создание директории для логов
if (-not (Test-Path "C:\temp")) {
    New-Item -ItemType Directory -Path "C:\temp" -Force | Out-Null
}

# Запуск деплоя
$success = Invoke-Deploy

if ($success) {
    Write-Host ""
    Write-Log "Готово!" "OK"
    Write-Log "Лог сохранён: $DEPLOY_LOG" "INFO"
    
    $showLogs = Read-Host "Показать логи бота? (y/n)"
    if ($showLogs -eq 'y' -or $showLogs -eq 'Y') {
        ssh $SERVER_SSH "cd $SERVER_PATH && docker compose logs -f --tail=50 bot"
    }
} else {
    Write-Host ""
    Write-Log "Деплой не удался!" "ERROR"
    exit 1
}
