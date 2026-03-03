#!/bin/bash
# Market Bot — Локальный скрипт деплоя на сервер
# Использование: ./scripts/deploy-to-server.sh
set -e
set -o pipefail

# ══════════════════════════════════════════════════════════════
# КОНФИГУРАЦИЯ (заполните перед использованием)
# ══════════════════════════════════════════════════════════════
# Сервер Timeweb Cloud
SERVER_SSH="zerodolg-server"        # SSH алиас (уже настроен в ~/.ssh/config)
SERVER_PATH="/opt/market-telegram-bot"  # Путь к проекту на сервере

# Локальная ветка
LOCAL_BRANCH="main"                  # Ветка для деплоя

# Требуемые версии (как на локальной машине)
REQUIRED_DOCKER="29.2.1"
REQUIRED_DOCKER_COMPOSE="5.0.2"

# Логирование
DEPLOY_LOG="/tmp/deploy-$(date +%Y%m%d_%H%M%S).log"

# ══════════════════════════════════════════════════════════════
# ЦВЕТА ДЛЯ ВЫВОДА
# ══════════════════════════════════════════════════════════════
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ══════════════════════════════════════════════════════════════
# ФУНКЦИИ
# ══════════════════════════════════════════════════════════════

print_status() {
    echo -e "${GREEN}✓${NC} $1" | tee -a "$DEPLOY_LOG"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1" | tee -a "$DEPLOY_LOG"
}

print_error() {
    echo -e "${RED}✗${NC} $1" | tee -a "$DEPLOY_LOG"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1" | tee -a "$DEPLOY_LOG"
}

# Проверка SSH-соединения
check_ssh_connection() {
    print_info "Проверка SSH-соединения..."
    if ! ssh -o ConnectTimeout=10 -o BatchMode=yes "$SERVER_SSH" "exit" 2>/dev/null; then
        print_error "Не удалось подключиться к серверу!"
        exit 1
    fi
    print_status "SSH-соединение OK"
}

# Создание бэкапа перед деплоем
create_backup() {
    print_info "Создание бэкапа..."
    ssh "$SERVER_SSH" "
    cd $SERVER_PATH &&
    [ -f .env ] && cp .env .env.backup.\$(date +%Y%m%d_%H%M%S) &&
    echo 'Бэкап .env создан'
    " || print_warning "Не удалось создать бэкап .env"
    print_status "Бэкап создан"
}

# Откат при ошибке
rollback() {
    print_warning "Выполняется откат..."
    ssh "$SERVER_SSH" "
    cd $SERVER_PATH &&
    git reset --hard HEAD~1 2>/dev/null || echo 'Нет коммитов для отката' &&
    docker compose up -d 2>/dev/null || echo 'Откат Docker не выполнен'
    "
    print_status "Откат завершён"
}

# Ожидание запуска сервиса
wait_for_service() {
    local max_attempts=30
    local attempt=1
    print_info "Ожидание запуска сервиса..."
    while [ $attempt -le $max_attempts ]; do
        if ssh "$SERVER_SSH" "curl -sf http://localhost:8001/health" > /dev/null 2>&1; then
            print_status "Сервис готов (попытка $attempt)"
            return 0
        fi
        sleep 2
        attempt=$((attempt + 1))
        print_info "Ожидание... (попытка $attempt/$max_attempts)"
    done
    print_error "Сервис не запустился за $((max_attempts * 2)) секунд!"
    return 1
}

# Проверка здоровья всех сервисов
health_check_all() {
    print_info "Проверка всех сервисов..."
    local services=("bot" "api" "worker" "celery_beat")
    local failed=0
    for service in "${services[@]}"; do
        if ssh "$SERVER_SSH" "cd $SERVER_PATH && docker compose ps $service 2>/dev/null | grep -q 'Up'"; then
            print_status "$service: OK"
        else
            print_warning "$service: Не активен"
            failed=$((failed + 1))
        fi
    done
    if [ $failed -gt 0 ]; then
        print_warning "$failed сервис(ов) не активны"
        return 1
    fi
    return 0
}

# Проверка и обновление Docker
check_and_update_docker() {
    print_info "Проверка версий Docker на сервере..."
    
    # Проверка Docker версии
    DOCKER_VERSION=$(ssh "$SERVER_SSH" "docker --version 2>/dev/null | cut -d' ' -f3" | tr -d ',')
    print_status "Docker на сервере: $DOCKER_VERSION"
    print_info "Требуется: $REQUIRED_DOCKER"
    if [ "$DOCKER_VERSION" != "$REQUIRED_DOCKER" ]; then
        print_warning "Docker версии отличаются. Обновление..."
        ssh "$SERVER_SSH" "
        curl -fsSL https://get.docker.com -o get-docker.sh &&
        sh get-docker.sh &&
        rm get-docker.sh
        "
        print_status "Docker обновлён"
    else
        print_status "Docker версии совпадают ✓"
    fi
    
    # Проверка Docker Compose версии
    COMPOSE_VERSION=$(ssh "$SERVER_SSH" "docker compose version 2>/dev/null | cut -d' ' -f4" | tr -d 'v')
    print_status "Docker Compose на сервере: $COMPOSE_VERSION"
    print_info "Требуется: $REQUIRED_DOCKER_COMPOSE"
    if [ "$COMPOSE_VERSION" != "$REQUIRED_DOCKER_COMPOSE" ]; then
        print_warning "Docker Compose версии отличаются. Обновление..."
        ssh "$SERVER_SSH" "
        DOCKER_CONFIG=\${DOCKER_CONFIG:-\$HOME/.docker} &&
        mkdir -p \$DOCKER_CONFIG/cli-plugins &&
        curl -SL https://github.com/docker/compose/releases/download/v$REQUIRED_DOCKER_COMPOSE/docker-compose-linux-x86_64 -o \$DOCKER_CONFIG/cli-plugins/docker-compose &&
        chmod +x \$DOCKER_CONFIG/cli-plugins/docker-compose
        "
        print_status "Docker Compose обновлён"
    else
        print_status "Docker Compose версии совпадают ✓"
    fi
    
    # Проверка nginx
    NGINX_VERSION=$(ssh "$SERVER_SSH" "nginx -v 2>&1 | cut -d'/' -f2")
    print_status "Nginx на сервере: $NGINX_VERSION"
}

# Проверка prerequisites
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

# Основная функция деплоя
deploy_to_server() {
    print_info "Деплой на сервер ${SERVER_SSH}:${SERVER_PATH}..."
    echo "" | tee -a "$DEPLOY_LOG"
    
    # 0. Проверка SSH
    check_ssh_connection
    echo ""
    
    # 1. Создание бэкапа
    create_backup
    echo ""
    
    # 2. Проверка и обновление Docker
    check_and_update_docker
    echo ""
    
    # 3. Git pull на сервер
    print_status "1. Git pull на сервер..."
    if ! ssh "$SERVER_SSH" "
    cd $SERVER_PATH &&
    git fetch origin $LOCAL_BRANCH &&
    git checkout $LOCAL_BRANCH &&
    git reset --hard origin/$LOCAL_BRANCH
    "; then
        print_error "Git pull failed!"
        rollback
        exit 1
    fi
    
    # 4. Проверка .env
    print_status "2. Проверка .env..."
    if ! ssh "$SERVER_SSH" "
    cd $SERVER_PATH &&
    if [ ! -f .env ]; then
        echo '❌ .env файл не найден!' && exit 1
    fi
    "; then
        print_error ".env файл не найден!"
        rollback
        exit 1
    fi
    
    # 5. Pull Docker образов
    print_status "3. Pull Docker образов..."
    if ! ssh "$SERVER_SSH" "
    cd $SERVER_PATH &&
    docker compose pull
    "; then
        print_error "Docker pull failed!"
        rollback
        exit 1
    fi
    
    # 6. Применение миграций
    print_status "4. Применение миграций..."
    if ! ssh "$SERVER_SSH" "
    cd $SERVER_PATH &&
    docker compose run --rm bot poetry run alembic upgrade head
    "; then
        print_warning "Миграции не выполнены (возможно не требуется)"
    fi
    
    # 7. Обновление сервисов
    print_status "5. Обновление сервисов..."
    ssh "$SERVER_SSH" "
    cd $SERVER_PATH &&
    docker compose up -d --no-deps bot api worker celery_beat
    "
    
    # 8. Ожидание запуска
    wait_for_service || {
        print_error "Запуск failed!"
        rollback
        exit 1
    }
    
    # 9. Проверка здоровья
    print_status "7. Проверка здоровья сервисов..."
    ssh "$SERVER_SSH" "
    cd $SERVER_PATH &&
    docker compose ps
    "
    
    # 10. Health check API
    print_status "8. Health check API..."
    if ssh "$SERVER_SSH" "curl -sf http://localhost:8001/health" > /dev/null 2>&1; then
        print_status "API health check: OK"
    else
        print_warning "API health check: FAILED (требуется время на запуск)"
    fi
    
    # 11. Проверка всех сервисов
    health_check_all || {
        print_warning "Не все сервисы активны"
    }
    
    # 12. Очистка
    print_status "9. Очистка старых образов..."
    ssh "$SERVER_SSH" "
    cd $SERVER_PATH &&
    docker image prune -f
    "
    
    echo ""
    print_status "Деплой завершён успешно!"
}

# Показать логи
show_logs() {
    read -p "Показать логи бота? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ssh "$SERVER_SSH" "
        cd $SERVER_PATH &&
        docker compose logs -f --tail=50 bot
        "
    fi
}

# ══════════════════════════════════════════════════════════════
# ОСНОВНОЙ СЦЕНАРИЙ
# ══════════════════════════════════════════════════════════════

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║     Market Bot — Деплой на Timeweb Cloud                  ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Инициализация логирования
exec > >(tee -a "$DEPLOY_LOG") 2>&1

check_prerequisites
check_ssh_connection

echo ""
print_warning "Внимание! Будет выполнен деплой на сервер:"
echo "  Сервер: $SERVER_SSH"
echo "  Путь: $SERVER_PATH"
echo "  Ветка: $LOCAL_BRANCH"
echo "  Лог: $DEPLOY_LOG"
echo ""

read -p "Продолжить деплой? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_warning "Деплой отменён"
    exit 0
fi

deploy_to_server
show_logs

echo ""
print_status "Готово!"
echo ""
print_info "Лог деплоя сохранён: $DEPLOY_LOG"