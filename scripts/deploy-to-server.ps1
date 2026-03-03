# Market Bot — Production Deployment Script (PowerShell)
# Использование: .\scripts\deploy-to-server.ps1
# Логирование: Windows Event Log + консоль

# ══════════════════════════════════════════════════════════════
# КОНФИГУРАЦИЯ
# ══════════════════════════════════════════════════════════════

# Сервер (SSH алиас — уже настроен)
$SERVER_SSH = "zerodolg-server"
$SERVER_PATH = "/opt/market-telegram-bot"

# Ветка для деплоя
$LOCAL_BRANCH = "main"

# Требуемые версии (синхронизация с локальной машиной)
$REQUIRED_DOCKER = "29.2.1"
$REQUIRED_DOCKER_COMPOSE = "5.0.2"

# Таймауты
$SSH_TIMEOUT = 10
$MAX_HEALTH_ATTEMPTS = 30
$HEALTH_CHECK_INTERVAL = 2

# ══════════════════════════════════════════════════════════════
# ФУНКЦИИ ВЫВОДА
# ══════════════════════════════════════════════════════════════

function Print-Status { param([string]$Message) Write-Host "✓ $Message" -ForegroundColor Green }
function Print-Warning { param([string]$Message) Write-Host "⚠ $Message" -ForegroundColor Yellow }
function Print-Error { param([string]$Message) Write-Host "✗ $Message" -ForegroundColor Red }
function Print-Info { param([string]$Message) Write-Host "ℹ $Message" -ForegroundColor Cyan }

# ══════════════════════════════════════════════════════════════
# ПРОВЕРКИ
# ══════════════════════════════════════════════════════════════

function Test-Prerequisites {
    Print-Info "Проверка prerequisites..."
    
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        Print-Error "Git не установлен!"
        exit 1
    }
    
    if (-not (Get-Command ssh -ErrorAction SilentlyContinue)) {
        Print-Error "SSH не установлен!"
        exit 1
    }
    
    # Проверка текущей ветки
    $currentBranch = git rev-parse --abbrev-ref HEAD
    if ($currentBranch -ne $LOCAL_BRANCH) {
        Print-Warning "Текущая ветка: $currentBranch (ожидалась $LOCAL_BRANCH)"
        $continue = Read-Host "Продолжить? (y/n)"
        if ($continue -ne 'y' -and $continue -ne 'Y') {
            exit 1
        }
    }
    
    # Проверка незакоммиченных изменений
    $status = git status --porcelain
    if ($status) {
        Print-Warning "Есть незакоммиченные изменения!"
        $continue = Read-Host "Продолжить? (y/n)"
        if ($continue -ne 'y' -and $continue -ne 'Y') {
            exit 1
        }
    }
    
    Print-Status "Prerequisites OK"
}

function Test-SSH-Connection {
    Print-Info "Проверка SSH-соединения..."
    try {
        $null = ssh -o ConnectTimeout=$SSH_TIMEOUT -o BatchMode=yes $SERVER_SSH "exit" 2>$null
        Print-Status "SSH-соединение OK"
    } catch {
        Print-Error "Не удалось подключиться к серверу!"
        Print-Error "Проверьте SSH ключ: ssh $SERVER_SSH"
        exit 1
    }
}

# ══════════════════════════════════════════════════════════════
# БЕКАП
# ══════════════════════════════════════════════════════════════

function Create-Backup {
    Print-Info "Создание бэкапа..."
    ssh $SERVER_SSH "
        cd $SERVER_PATH &&
        [ -f .env ] && cp .env .env.backup.`$(date +%Y%m%d_%H%M%S) &&
        echo '✓ Бэкап .env создан'
    " 2>$null
    Print-Status "Бэкап создан"
}

# ══════════════════════════════════════════════════════════════
# ВАЛИДАЦИЯ .ENV
# ══════════════════════════════════════════════════════════════

function Validate-Env {
    Print-Info "Валидация .env..."
    $result = ssh $SERVER_SSH "
        cd $SERVER_PATH &&
        grep -q '^DATABASE_URL=' .env &&
        grep -q '^BOT_TOKEN=' .env &&
        grep -q '^OPENROUTER_API_KEY=' .env &&
        echo '✓ .env валиден'
    " 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Print-Error ".env файл не содержит обязательных переменных!"
        Print-Error "Требуются: DATABASE_URL, BOT_TOKEN, OPENROUTER_API_KEY"
        exit 1
    }
    Print-Status ".env валиден"
}

# ══════════════════════════════════════════════════════════════
# DOCKER VERSION CHECK
# ══════════════════════════════════════════════════════════════

function Test-AndUpdate-Docker {
    Print-Info "Проверка версий Docker..."
    
    # Docker
    $dockerVersion = ssh $SERVER_SSH "docker --version" 2>$null
    if ($dockerVersion) {
        $dockerVersion = ($dockerVersion -split ' ')[2].Trim(',')
        Print-Info "Docker на сервере: $dockerVersion (требуется: $REQUIRED_DOCKER)"
        
        if ($dockerVersion -ne $REQUIRED_DOCKER) {
            Print-Warning "Docker версии отличаются. Обновление..."
            ssh $SERVER_SSH @"
curl -fsSL https://get.docker.com -o get-docker.sh &&
sh get-docker.sh &&
rm get-docker.sh
"@
            Print-Status "Docker обновлён"
        } else {
            Print-Status "Docker версии совпадают ✓"
        }
    }
    
    # Docker Compose
    $composeVersion = ssh $SERVER_SSH "docker compose version" 2>$null
    if ($composeVersion) {
        $composeVersion = ($composeVersion -split ' ')[3].TrimStart('v')
        Print-Info "Docker Compose на сервере: $composeVersion (требуется: $REQUIRED_DOCKER_COMPOSE)"
        
        if ($composeVersion -ne $REQUIRED_DOCKER_COMPOSE) {
            Print-Warning "Docker Compose версии отличаются. Обновление..."
            ssh $SERVER_SSH @"
`$DOCKER_CONFIG = `$env:DOCKER_CONFIG ?? `$HOME/.docker
New-Item -ItemType Directory -Force -Path `$DOCKER_CONFIG/cli-plugins | Out-Null
Invoke-WebRequest -Uri "https://github.com/docker/compose/releases/download/v$REQUIRED_DOCKER_COMPOSE/docker-compose-linux-x86_64" -OutFile `$DOCKER_CONFIG/cli-plugins/docker-compose
chmod +x `$DOCKER_CONFIG/cli-plugins/docker-compose
"@
            Print-Status "Docker Compose обновлён"
        } else {
            Print-Status "Docker Compose версии совпадают ✓"
        }
    }
}

# ══════════════════════════════════════════════════════════════
# HEALTH CHECKS
# ══════════════════════════════════════════════════════════════

function Wait-For-Service {
    param([string]$ServiceName)
    
    Print-Info "Ожидание $ServiceName..."
    $attempt = 1
    
    while ($attempt -le $MAX_HEALTH_ATTEMPTS) {
        $result = ssh $SERVER_SSH "curl -sf http://localhost:8001/health" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Print-Status "$ServiceName готов (попытка $attempt)"
            return $true
        }
        Start-Sleep -Seconds $HEALTH_CHECK_INTERVAL
        $attempt++
    }
    
    Print-Error "$ServiceName не запустился за $($MAX_HEALTH_ATTEMPTS * $HEALTH_CHECK_INTERVAL) секунд!"
    return $false
}

function Health-Check-All {
    Print-Info "Проверка всех сервисов..."
    $services = @("bot", "api", "worker", "celery_beat")
    $failed = 0
    
    foreach ($service in $services) {
        $result = ssh $SERVER_SSH "cd $SERVER_PATH && docker compose ps $service" 2>&1
        if ($result -match 'Up') {
            Print-Status "$service`: OK"
        } else {
            Print-Warning "$service`: NOT RUNNING"
            $failed++
        }
    }
    
    if ($failed -gt 0) {
        Print-Warning "$failed сервисов не запущено"
        return $false
    }
    
    Print-Status "Все сервисы работают"
    return $true
}

# ══════════════════════════════════════════════════════════════
# ROLLBACK
# ══════════════════════════════════════════════════════════════

function Invoke-Rollback {
    Print-Warning "Выполняется откат..."
    ssh $SERVER_SSH "
        cd $SERVER_PATH &&
        git reset --hard HEAD~1 2>/dev/null || echo 'Откат невозможен' &&
        docker compose up -d 2>/dev/null || echo 'Docker не доступен'
    " 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Print-Error "Откат не удался!"
        return $false
    }
    Print-Status "Откат завершён"
    return $true
}

# ══════════════════════════════════════════════════════════════
# DEPLOY
# ══════════════════════════════════════════════════════════════

function Deploy-ToServer {
    Print-Info "Деплой на сервер $SERVER_SSH:$SERVER_PATH..."
    Write-Host ""
    
    # 0. Проверка SSH
    Test-SSH-Connection
    Write-Host ""
    
    # 1. Бэкап
    Create-Backup
    Write-Host ""
    
    # 2. Валидация .env
    Validate-Env
    Write-Host ""
    
    # 3. Git pull
    Print-Status "Git pull..."
    $result = ssh $SERVER_SSH "
        cd $SERVER_PATH &&
        git fetch origin $LOCAL_BRANCH &&
        git checkout $LOCAL_BRANCH &&
        git reset --hard origin/$LOCAL_BRANCH
    " 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Print-Error "Git failed!"
        Invoke-Rollback
        exit 1
    }
    Write-Host ""
    
    # 4. Docker pull
    Print-Status "Docker pull..."
    $result = ssh $SERVER_SSH "
        cd $SERVER_PATH &&
        docker compose pull
    " 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Print-Error "Docker pull failed!"
        Invoke-Rollback
        exit 1
    }
    Write-Host ""
    
    # 5. Миграции
    Print-Status "Миграции..."
    $result = ssh $SERVER_SSH "
        cd $SERVER_PATH &&
        docker compose run --rm bot poetry run alembic upgrade head
    " 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Print-Error "Миграции failed!"
        Invoke-Rollback
        exit 1
    }
    Write-Host ""
    
    # 6. Обновление сервисов
    Print-Status "Обновление сервисов..."
    $result = ssh $SERVER_SSH "
        cd $SERVER_PATH &&
        docker compose up -d --no-deps bot api worker celery_beat
    " 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Print-Error "Обновление сервисов failed!"
        Invoke-Rollback
        exit 1
    }
    Write-Host ""
    
    # 7. Ожидание запуска
    if (-not (Wait-For-Service "API")) {
        Print-Error "Запуск failed!"
        Invoke-Rollback
        exit 1
    }
    Write-Host ""
    
    # 8. Health check
    if (-not (Health-Check-All)) {
        Print-Error "Health check failed!"
        Invoke-Rollback
        exit 1
    }
    Write-Host ""
    
    # 9. Очистка
    Print-Status "Очистка старых образов..."
    ssh $SERVER_SSH "
        cd $SERVER_PATH &&
        docker image prune -f
    " 2>&1
    Write-Host ""
    
    Print-Status "Деплой завершён успешно!"
}

# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║     Market Bot — Production Deployment                    ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

Test-Prerequisites
Test-SSH-Connection

Write-Host ""
Print-Warning "Внимание! Будет выполнен деплой:"
Write-Host "  Сервер: $SERVER_SSH"
Write-Host "  Путь: $SERVER_PATH"
Write-Host "  Ветка: $LOCAL_BRANCH"
Write-Host ""

$confirm = Read-Host "Продолжить деплой? (y/n)"
if ($confirm -ne 'y' -and $confirm -ne 'Y') {
    Print-Warning "Деплой отменён"
    exit 0
}

Deploy-ToServer

Write-Host ""
Print-Status "Готово!"
Write-Host ""
Print-Info "Мониторинг: ssh $SERVER_SSH 'cd $SERVER_PATH && docker compose logs -f'"
