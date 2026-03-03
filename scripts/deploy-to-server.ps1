# Market Bot — Локальный скрипт деплоя на сервер (PowerShell)
# Использование: .\scripts\deploy-to-server.ps1

# ══════════════════════════════════════════════════════════════
# КОНФИГУРАЦИЯ (заполните перед использованием)
# ══════════════════════════════════════════════════════════════

# Сервер Timeweb Cloud
$SERVER_HOST = "123.45.67.89"          # IP вашего сервера
$SERVER_PORT = "22"                     # SSH порт (обычно 22)
$SERVER_USER = "root"                   # Пользователь
$SERVER_PATH = "/opt/market-telegram-bot"  # Путь к проекту на сервере

# Локальная ветка
$LOCAL_BRANCH = "main"                  # Ветка для деплоя

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
    Print-Info "Деплой на сервер $SERVER_USER@$SERVER_HOST:$SERVER_PATH..."
    Write-Host ""
    
    # 1. Git push на сервер
    Print-Status "1. Git push на сервер..."
    Invoke-SSHCommand "
        cd $SERVER_PATH &&
        git fetch origin $LOCAL_BRANCH &&
        git checkout $LOCAL_BRANCH &&
        git reset --hard origin/$LOCAL_BRANCH
    "
    
    # 2. Проверка .env
    Print-Status "2. Проверка .env..."
    Invoke-SSHCommand "
        cd $SERVER_PATH &&
        if [ ! -f .env ]; then
            echo '❌ .env файл не найден!' && exit 1
        fi
    "
    
    # 3. Pull Docker образов
    Print-Status "3. Pull Docker образов..."
    Invoke-SSHCommand "
        cd $SERVER_PATH &&
        docker compose pull
    "
    
    # 4. Применение миграций
    Print-Status "4. Применение миграций..."
    Invoke-SSHCommand "
        cd $SERVER_PATH &&
        docker compose run --rm bot poetry run alembic upgrade head
    "
    
    # 5. Обновление сервисов
    Print-Status "5. Обновление сервисов..."
    Invoke-SSHCommand "
        cd $SERVER_PATH &&
        docker compose up -d --no-deps bot api worker celery_beat
    "
    
    # 6. Ожидание запуска
    Print-Status "6. Ожидание запуска (15 сек)..."
    Start-Sleep -Seconds 15
    
    # 7. Проверка здоровья
    Print-Status "7. Проверка здоровья сервисов..."
    Invoke-SSHCommand "
        cd $SERVER_PATH &&
        docker compose ps
    "
    
    # 8. Health check API
    Print-Status "8. Health check API..."
    $apiCheck = Invoke-SSHCommand "curl -f http://localhost:8001/health" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Print-Status "API health check: OK"
    } else {
        Print-Warning "API health check: FAILED (требуется время на запуск)"
    }
    
    # 9. Очистка
    Print-Status "9. Очистка старых образов..."
    Invoke-SSHCommand "
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
