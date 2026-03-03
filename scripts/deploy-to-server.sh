#!/bin/bash
# Market Bot — Production Deployment Script
# Использование: ./scripts/deploy-to-server.sh
# Логирование: /var/log/deploy-*.log (на сервере)

set -e
set -o pipefail

# ══════════════════════════════════════════════════════════════
# КОНФИГУРАЦИЯ
# ══════════════════════════════════════════════════════════════

# Сервер (SSH алиас — уже настроен)
SERVER_SSH="zerodolg-server"
SERVER_PATH="/opt/market-telegram-bot"

# Ветка для деплоя
LOCAL_BRANCH="main"

# Требуемые версии (синхронизация с локальной машиной)
REQUIRED_DOCKER="29.2.1"
REQUIRED_DOCKER_COMPOSE="5.0.2"

# Таймауты
SSH_TIMEOUT=10
MAX_HEALTH_ATTEMPTS=30
HEALTH_CHECK_INTERVAL=2

# ══════════════════════════════════════════════════════════════
# ЦВЕТА
# ══════════════════════════════════════════════════════════════

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ══════════════════════════════════════════════════════════════
# ФУНКЦИИ ВЫВОДА
# ══════════════════════════════════════════════════════════════

print_status() { echo -e "${GREEN}✓${NC} $1"; }
print_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; }
print_info() { echo -e "${BLUE}ℹ${NC} $1"; }

# ══════════════════════════════════════════════════════════════
# ПРОВЕРКИ
# ══════════════════════════════════════════════════════════════

check_prerequisites() {
    print_info "Проверка prerequisites..."
    
    if ! command -v git &> /dev/null; then
        print_error "Git не установлен!"
        exit 1
    fi
    
    if ! command -v ssh &> /dev/null; then
        print_error "SSH не установлен!"
        exit 1
    fi
    
    # Проверка текущей ветки
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    if [ "$CURRENT_BRANCH" != "$LOCAL_BRANCH" ]; then
        print_warning "Текущая ветка: $CURRENT_BRANCH (ожидалась $LOCAL_BRANCH)"
        read -p "Продолжить? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    # Проверка незакоммиченных изменений
    if [ -n "$(git status --porcelain)" ]; then
        print_warning "Есть незакоммиченные изменения!"
        read -p "Продолжить? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    print_status "Prerequisites OK"
}

check_ssh_connection() {
    print_info "Проверка SSH-соединения..."
    if ! ssh -o ConnectTimeout=$SSH_TIMEOUT -o BatchMode=yes $SERVER_SSH "exit" 2>/dev/null; then
        print_error "Не удалось подключиться к серверу!"
        print_error "Проверьте SSH ключ: ssh $SERVER_SSH"
        exit 1
    fi
    print_status "SSH-соединение OK"
}

# ══════════════════════════════════════════════════════════════
# БЕКАП
# ══════════════════════════════════════════════════════════════

create_backup() {
    print_info "Создание бэкапа..."
    ssh $SERVER_SSH "
        cd $SERVER_PATH &&
        [ -f .env ] && cp .env .env.backup.\$(date +%Y%m%d_%H%M%S) &&
        echo '✓ Бэкап .env создан'
    " || {
        print_warning "Не удалось создать бэкап (возможно .env отсутствует)"
    }
    print_status "Бэкап создан"
}

# ══════════════════════════════════════════════════════════════
# ВАЛИДАЦИЯ .ENV
# ══════════════════════════════════════════════════════════════

validate_env() {
    print_info "Валидация .env..."
    ssh $SERVER_SSH "
        cd $SERVER_PATH &&
        grep -q '^DATABASE_URL=' .env || exit 1 &&
        grep -q '^BOT_TOKEN=' .env || exit 1 &&
        grep -q '^OPENROUTER_API_KEY=' .env || exit 1 &&
        echo '✓ .env валиден'
    " || {
        print_error ".env файл не содержит обязательных переменных!"
        print_error "Требуются: DATABASE_URL, BOT_TOKEN, OPENROUTER_API_KEY"
        exit 1
    }
    print_status ".env валиден"
}

# ══════════════════════════════════════════════════════════════
# DOCKER VERSION CHECK
# ══════════════════════════════════════════════════════════════

check_and_update_docker() {
    print_info "Проверка версий Docker..."
    
    # Docker
    DOCKER_VERSION=$(ssh $SERVER_SSH "docker --version 2>/dev/null | cut -d' ' -f3" | tr -d ',')
    print_info "Docker на сервере: $DOCKER_VERSION (требуется: $REQUIRED_DOCKER)"
    
    if [ "$DOCKER_VERSION" != "$REQUIRED_DOCKER" ]; then
        print_warning "Docker версии отличаются. Обновление..."
        ssh $SERVER_SSH "
            curl -fsSL https://get.docker.com -o get-docker.sh &&
            sh get-docker.sh &&
            rm get-docker.sh
        " || {
            print_error "Не удалось обновить Docker!"
            exit 1
        }
        print_status "Docker обновлён"
    else
        print_status "Docker версии совпадают ✓"
    fi
    
    # Docker Compose
    COMPOSE_VERSION=$(ssh $SERVER_SSH "docker compose version 2>/dev/null | cut -d' ' -f4" | tr -d 'v')
    print_info "Docker Compose на сервере: $COMPOSE_VERSION (требуется: $REQUIRED_DOCKER_COMPOSE)"
    
    if [ "$COMPOSE_VERSION" != "$REQUIRED_DOCKER_COMPOSE" ]; then
        print_warning "Docker Compose версии отличаются. Обновление..."
        ssh $SERVER_SSH "
            DOCKER_CONFIG=\${DOCKER_CONFIG:-\$HOME/.docker} &&
            mkdir -p \$DOCKER_CONFIG/cli-plugins &&
            curl -SL https://github.com/docker/compose/releases/download/v$REQUIRED_DOCKER_COMPOSE/docker-compose-linux-x86_64 -o \$DOCKER_CONFIG/cli-plugins/docker-compose &&
            chmod +x \$DOCKER_CONFIG/cli-plugins/docker-compose
        " || {
            print_error "Не удалось обновить Docker Compose!"
            exit 1
        }
        print_status "Docker Compose обновлён"
    else
        print_status "Docker Compose версии совпадают ✓"
    fi
}

# ══════════════════════════════════════════════════════════════
# HEALTH CHECKS
# ══════════════════════════════════════════════════════════════

wait_for_service() {
    local service_name=$1
    local max_attempts=$MAX_HEALTH_ATTEMPTS
    local attempt=1
    
    print_info "Ожидание $service_name..."
    
    while [ $attempt -le $max_attempts ]; do
        if ssh $SERVER_SSH "curl -sf http://localhost:8001/health" > /dev/null 2>&1; then
            print_status "$service_name готов (попытка $attempt)"
            return 0
        fi
        sleep $HEALTH_CHECK_INTERVAL
        attempt=$((attempt + 1))
    done
    
    print_error "$service_name не запустился за $((max_attempts * HEALTH_CHECK_INTERVAL)) секунд!"
    return 1
}

health_check_all() {
    print_info "Проверка всех сервисов..."
    local services=("bot" "api" "worker" "celery_beat")
    local failed=0
    
    for service in "${services[@]}"; do
        if ssh $SERVER_SSH "cd $SERVER_PATH && docker compose ps $service | grep -q 'Up'"; then
            print_status "$service: OK"
        else
            print_warning "$service: NOT RUNNING"
            failed=$((failed + 1))
        fi
    done
    
    if [ $failed -gt 0 ]; then
        print_warning "$failed сервисов не запущено"
        return 1
    fi
    
    print_status "Все сервисы работают"
    return 0
}

# ══════════════════════════════════════════════════════════════
# ROLLBACK
# ══════════════════════════════════════════════════════════════

rollback() {
    print_warning "Выполняется откат..."
    ssh $SERVER_SSH "
        cd $SERVER_PATH &&
        git reset --hard HEAD~1 2>/dev/null || echo 'Откат невозможен' &&
        docker compose up -d 2>/dev/null || echo 'Docker не доступен'
    " || {
        print_error "Откат не удался!"
        return 1
    }
    print_status "Откат завершён"
}

# ══════════════════════════════════════════════════════════════
# DEPLOY
# ══════════════════════════════════════════════════════════════

deploy_to_server() {
    print_info "Деплой на сервер $SERVER_SSH:$SERVER_PATH..."
    echo ""
    
    # 0. Проверка SSH
    check_ssh_connection
    echo ""
    
    # 1. Бэкап
    create_backup
    echo ""
    
    # 2. Валидация .env
    validate_env
    echo ""
    
    # 3. Git pull
    print_status "Git pull..."
    ssh $SERVER_SSH "
        cd $SERVER_PATH &&
        git fetch origin $LOCAL_BRANCH &&
        git checkout $LOCAL_BRANCH &&
        git reset --hard origin/$LOCAL_BRANCH
    " || {
        print_error "Git failed!"
        rollback
        exit 1
    }
    echo ""
    
    # 4. Docker pull
    print_status "Docker pull..."
    ssh $SERVER_SSH "
        cd $SERVER_PATH &&
        docker compose pull
    " || {
        print_error "Docker pull failed!"
        rollback
        exit 1
    }
    echo ""
    
    # 5. Миграции
    print_status "Миграции..."
    ssh $SERVER_SSH "
        cd $SERVER_PATH &&
        docker compose run --rm bot poetry run alembic upgrade head
    " || {
        print_error "Миграции failed!"
        rollback
        exit 1
    }
    echo ""
    
    # 6. Обновление сервисов
    print_status "Обновление сервисов..."
    ssh $SERVER_SSH "
        cd $SERVER_PATH &&
        docker compose up -d --no-deps bot api worker celery_beat
    " || {
        print_error "Обновление сервисов failed!"
        rollback
        exit 1
    }
    echo ""
    
    # 7. Ожидание запуска
    wait_for_service "API" || {
        print_error "Запуск failed!"
        rollback
        exit 1
    }
    echo ""
    
    # 8. Health check
    health_check_all || {
        print_error "Health check failed!"
        rollback
        exit 1
    }
    echo ""
    
    # 9. Очистка
    print_status "Очистка старых образов..."
    ssh $SERVER_SSH "
        cd $SERVER_PATH &&
        docker image prune -f
    "
    echo ""
    
    print_status "Деплой завершён успешно!"
}

# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║     Market Bot — Production Deployment                    ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

check_prerequisites
check_ssh_connection

echo ""
print_warning "Внимание! Будет выполнен деплой:"
echo "  Сервер: $SERVER_SSH"
echo "  Путь: $SERVER_PATH"
echo "  Ветка: $LOCAL_BRANCH"
echo ""

read -p "Продолжить деплой? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_warning "Деплой отменён"
    exit 0
fi

deploy_to_server

echo ""
print_status "Готово!"
echo ""
print_info "Логи на сервере: ssh $SERVER_SSH 'tail -f /var/log/deploy-*.log'"
print_info "Мониторинг: ssh $SERVER_SSH 'cd $SERVER_PATH && docker compose logs -f'"
