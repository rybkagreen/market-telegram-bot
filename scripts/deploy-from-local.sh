#!/bin/bash
# Market Bot — Скрипт обновления с пересборкой Docker-контейнеров
# Использование: ./scripts/rebuild-and-deploy.sh
set -e
set -o pipefail

# ══════════════════════════════════════════════════════════════
# КОНФИГУРАЦИЯ
# ══════════════════════════════════════════════════════════════
SERVER_SSH="zerodolg-server"
SERVER_PATH="/opt/market-telegram-bot"
LOCAL_BRANCH="main"
DEPLOY_LOG="/tmp/rebuild-$(date +%Y%m%d_%H%M%S).log"

# Сервисы для пересборки (БЕЗ БД и кэша!)
SERVICES_TO_REBUILD=("bot" "api" "worker" "celery_beat" "nginx" "flower")

# ══════════════════════════════════════════════════════════════
# ЦВЕТА
# ══════════════════════════════════════════════════════════════
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ══════════════════════════════════════════════════════════════
# ФУНКЦИИ
# ══════════════════════════════════════════════════════════════

print_status() { echo -e "${GREEN}✓${NC} $1" | tee -a "$DEPLOY_LOG"; }
print_warning() { echo -e "${YELLOW}⚠${NC} $1" | tee -a "$DEPLOY_LOG"; }
print_error() { echo -e "${RED}✗${NC} $1" | tee -a "$DEPLOY_LOG"; }
print_info() { echo -e "${BLUE}ℹ${NC} $1" | tee -a "$DEPLOY_LOG"; }

# Проверка SSH
check_ssh_connection() {
    print_info "Проверка SSH-соединения..."
    if ! ssh -o ConnectTimeout=10 -o BatchMode=yes "$SERVER_SSH" "exit" 2>/dev/null; then
        print_error "Не удалось подключиться к серверу!"
        exit 1
    fi
    print_status "SSH-соединение OK"
}

# Бэкап перед обновлением
create_backup() {
    print_info "Создание бэкапа..."
    ssh "$SERVER_SSH" "
    cd $SERVER_PATH &&
    [ -f .env ] && cp .env .env.backup.\$(date +%Y%m%d_%H%M%S) &&
    docker compose ps -q > /tmp/container_ids_backup.txt &&
    echo 'Бэкап создан'
    " || print_warning "Не удалось создать бэкап"
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
    local service=$1
    local max_attempts=30
    local attempt=1
    print_info "Ожидание запуска $service..."
    while [ $attempt -le $max_attempts ]; do
        if ssh "$SERVER_SSH" "cd $SERVER_PATH && docker compose ps $service 2>/dev/null | grep -q 'Up'"; then
            print_status "$service: запущен (попытка $attempt)"
            return 0
        fi
        sleep 2
        attempt=$((attempt + 1))
    done
    print_error "$service: не запустился!"
    return 1
}

# Health check API
health_check_api() {
    print_info "Health check API..."
    local max_attempts=10
    local attempt=1
    while [ $attempt -le $max_attempts ]; do
        if ssh "$SERVER_SSH" "curl -sf http://localhost:8001/health" > /dev/null 2>&1; then
            print_status "API health check: OK"
            return 0
        fi
        sleep 2
        attempt=$((attempt + 1))
        print_info "Ожидание API... (попытка $attempt/$max_attempts)"
    done
    print_warning "API health check: FAILED"
    return 1
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
    
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    if [ "$CURRENT_BRANCH" != "$LOCAL_BRANCH" ]; then
        print_warning "Текущая ветка: $CURRENT_BRANCH (ожидалась $LOCAL_BRANCH)"
        read -p "Продолжить? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
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

# Основная функция обновления с пересборкой
rebuild_and_deploy() {
    print_info "Обновление с пересборкой на сервере ${SERVER_SSH}:${SERVER_PATH}..."
    echo "" | tee -a "$DEPLOY_LOG"
    
    # 0. Проверка SSH
    check_ssh_connection
    echo ""
    
    # 1. Бэкап
    create_backup
    echo ""
    
    # 2. Git pull (получаем свежие изменения)
    print_status "1. Получение изменений из репозитория..."
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
    
    # 3. Проверка .env
    print_status "2. Проверка .env..."
    if ! ssh "$SERVER_SSH" "[ -f $SERVER_PATH/.env ]"; then
        print_error ".env файл не найден!"
        rollback
        exit 1
    fi
    
    # 4. Пересборка Docker образов БЕЗ КЭША
    print_status "3. Пересборка Docker образов (без кэша)..."
    print_warning "Это может занять несколько минут..."
    if ! ssh "$SERVER_SSH" "
    cd $SERVER_PATH &&
    docker compose build --no-cache --pull ${SERVICES_TO_REBUILD[*]}
    "; then
        print_error "Docker build failed!"
        rollback
        exit 1
    fi
    
    # 5. Применение миграций
    print_status "4. Применение миграций..."
    ssh "$SERVER_SSH" "
    cd $SERVER_PATH &&
    docker compose run --rm bot poetry run alembic upgrade head
    " || print_warning "Миграции не выполнены"
    
    # 6. Остановка старых контейнеров
    print_status "5. Остановка старых контейнеров..."
    ssh "$SERVER_SSH" "
    cd $SERVER_PATH &&
    docker compose stop ${SERVICES_TO_REBUILD[*]}
    "
    
    # 7. Запуск обновлённых сервисов
    print_status "6. Запуск обновлённых сервисов..."
    ssh "$SERVER_SSH" "
    cd $SERVER_PATH &&
    docker compose up -d --no-deps ${SERVICES_TO_REBUILD[*]}
    "
    
    # 8. Ожидание запуска критических сервисов
    for service in "bot" "api" "nginx"; do
        wait_for_service "$service" || {
            print_error "Критический сервис $service не запустился!"
            rollback
            exit 1
        }
    done
    
    # 9. Health check API
    health_check_api
    
    # 10. Проверка всех контейнеров
    print_status "7. Статус всех контейнеров..."
    ssh "$SERVER_SSH" "
    cd $SERVER_PATH &&
    docker compose ps
    "
    
    # 11. Очистка старых образов
    print_status "8. Очистка старых образов..."
    ssh "$SERVER_SSH" "
    cd $SERVER_PATH &&
    docker image prune -f --filter 'until=24h'
    "
    
    echo ""
    print_status "Обновление с пересборкой завершено успешно!"
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
echo "║     Market Bot — Обновление с пересборкой Docker          ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Инициализация логирования
exec > >(tee -a "$DEPLOY_LOG") 2>&1

check_prerequisites
check_ssh_connection

echo ""
print_warning "Внимание! Будет выполнено обновление с пересборкой:"
echo "  Сервер: $SERVER_SSH"
echo "  Путь: $SERVER_PATH"
echo "  Ветка: $LOCAL_BRANCH"
echo "  Сервисы: ${SERVICES_TO_REBUILD[*]}"
echo "  Режим: BUILD --no-cache (без кэша)"
echo "  Лог: $DEPLOY_LOG"
echo ""
print_warning "⚠ Пересборка без кэша может занять 5-15 минут!"
echo ""

read -p "Продолжить обновление? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_warning "Обновление отменено"
    exit 0
fi

rebuild_and_deploy
show_logs

echo ""
print_status "Готово!"
print_info "Лог сохранён: $DEPLOY_LOG"