# Market Bot — Локальный скрипт деплоя на сервер (PowerShell)
# Использование: .\scripts\deploy-to-server.ps1

# ══════════════════════════════════════════════════════════════
# КОНФИГУРАЦИЯ (заполните перед использованием)
# ══════════════════════════════════════════════════════════════

# Сервер Timeweb Cloud
$SERVER_SSH = "zerodolg-server"        # SSH алиас (уже настроен)
$SERVER_PATH = "/opt/market-telegram-bot"  # Путь к проекту на сервере

# Локальная ветка
$LOCAL_BRANCH = "main"                  # Ветка для деплоя

# Требуемые версии (как на локальной машине)
$REQUIRED_DOCKER = "29.2.1"
$REQUIRED_DOCKER_COMPOSE = "5.0.2"

# ══════════════════════════════════════════════════════════════
# ФУНКЦИИ
# ══════════════════════════════════════════════════════════════

function Print-Status {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Print-Warning {
    param([string]$Message)
    Write-Host "⚠ $Message" -ForegroundColor Yellow
}

function Print-Error {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor Red
}

function Print-Info {
    param([string]$Message)
    Write-Host "ℹ $Message" -ForegroundColor Cyan
}

function Test-AndUpdate-Docker {
    Print-Info "Проверка версий Docker на сервере..."
    
    # Проверка Docker версии
    $dockerVersion = ssh $SERVER_SSH "docker --version" 2>$null
    if ($dockerVersion) {
        $dockerVersion = ($dockerVersion -split ' ')[2].Trim(',')
        Print-Status "Docker на сервере: $dockerVersion"
        Print-Info "Требуется: $REQUIRED_DOCKER"
        
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
    
    # Проверка Docker Compose версии
    $composeVersion = ssh $SERVER_SSH "docker compose version" 2>$null
    if ($composeVersion) {
        $composeVersion = ($composeVersion -split ' ')[3].TrimStart('v')
        Print-Status "Docker Compose на сервере: $composeVersion"
        Print-Info "Требуется: $REQUIRED_DOCKER_COMPOSE"
        
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

function Test-Prerequisites {
    Print-Info "Проверка prerequisites..."
    
    # Проверка Git
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        Print-Error "Git не установлен!"
        exit 1
    }
    
    # Проверка SSH
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

function Invoke-SSHCommand {
    param([string]$Command)
    
    $sshCmd = "ssh -p $SERVER_PORT $SERVER_USER@$SERVER_HOST `"$Command`""
    Write-Host "Executing: $sshCmd" -ForegroundColor Gray
    Invoke-Expression $sshCmd
}

function Deploy-ToServer {
    Print-Info "Деплой на сервер $SERVER_SSH:$SERVER_PATH..."
    Write-Host ""
    
    # 0. Проверка и обновление Docker
    Test-AndUpdate-Docker
    Write-Host ""
    
    # 1. Git push на сервер
    Print-Status "1. Git push на сервер..."
    ssh $SERVER_SSH "
        cd $SERVER_PATH &&
        git fetch origin $LOCAL_BRANCH &&
        git checkout $LOCAL_BRANCH &&
        git reset --hard origin/$LOCAL_BRANCH
    "
    
    # 2. Проверка .env
    Print-Status "2. Проверка .env..."
    ssh $SERVER_SSH "
        cd $SERVER_PATH &&
        if [ ! -f .env ]; then
            echo '❌ .env файл не найден!' && exit 1
        fi
    "
    
    # 3. Pull Docker образов
    Print-Status "3. Pull Docker образов..."
    ssh $SERVER_SSH "
        cd $SERVER_PATH &&
        docker compose pull
    "
    
    # 4. Применение миграций
    Print-Status "4. Применение миграций..."
    ssh $SERVER_SSH "
        cd $SERVER_PATH &&
        docker compose run --rm bot poetry run alembic upgrade head
    "
    
    # 5. Обновление сервисов
    Print-Status "5. Обновление сервисов..."
    ssh $SERVER_SSH "
        cd $SERVER_PATH &&
        docker compose up -d --no-deps bot api worker celery_beat
    "
    
    # 6. Ожидание запуска
    Print-Status "6. Ожидание запуска (15 сек)..."
    Start-Sleep -Seconds 15
    
    # 7. Проверка здоровья
    Print-Status "7. Проверка здоровья сервисов..."
    ssh $SERVER_SSH "
        cd $SERVER_PATH &&
        docker compose ps
    "
    
    # 8. Health check API
    Print-Status "8. Health check API..."
    $apiCheck = ssh $SERVER_SSH "curl -f http://localhost:8001/health" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Print-Status "API health check: OK"
    } else {
        Print-Warning "API health check: FAILED (возможно требуется больше времени)"
    }
    
    # 9. Очистка
    Print-Status "9. Очистка старых образов..."
    ssh $SERVER_SSH "
        cd $SERVER_PATH &&
        docker image prune -f
    "
    
    Write-Host ""
    Print-Status "Деплой завершён успешно!"
}

function Show-Logs {
    $showLogs = Read-Host "Показать логи бота? (y/n)"
    if ($showLogs -eq 'y' -or $showLogs -eq 'Y') {
        Invoke-SSHCommand "
            cd $SERVER_PATH &&
            docker compose logs -f --tail=50 bot
        "
    }
}

# ══════════════════════════════════════════════════════════════
# ОСНОВНОЙ СЦЕНАРИЙ
# ══════════════════════════════════════════════════════════════

Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║     Market Bot — Деплой на Timeweb Cloud                  ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

Test-Prerequisites

Write-Host ""
Print-Warning "Внимание! Будет выполнен деплой на сервер:"
Write-Host "  Хост: $SERVER_HOST:$SERVER_PORT"
Write-Host "  Пользователь: $SERVER_USER"
Write-Host "  Путь: $SERVER_PATH"
Write-Host "  Ветка: $LOCAL_BRANCH"
Write-Host ""

$confirm = Read-Host "Продолжить деплой? (y/n)"
if ($confirm -ne 'y' -and $confirm -ne 'Y') {
    Print-Warning "Деплой отменён"
    exit 0
}

Deploy-ToServer
Show-Logs

Write-Host ""
Print-Status "Готово!"
