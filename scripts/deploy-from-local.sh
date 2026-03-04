#!/bin/bash
# Market Bot — Деплой с локального кода на сервер (без Git)
# Использование: ./scripts/deploy-from-local.sh
# 
# Этот скрипт копирует код с локальной машины на сервер
# и пересобирает Docker контейнеры.
# Идеально подходит для деплоя без коммитов в Git.

set -e
set -o pipefail

# ══════════════════════════════════════════════════════════════
# КОНФИГУРАЦИЯ
# ══════════════════════════════════════════════════════════════
SERVER_SSH="zerodolg-server"
SERVER_PATH="/opt/market-telegram-bot"
DEPLOY_LOG="/tmp/deploy-local-$(date +%Y%m%d_%H%M%S).log"

# Сервисы для пересборки (БЕЗ БД и кэша!)
SERVICES_TO_REBUILD=("bot" "api" "worker" "celery_beat" "nginx" "flower")

# Файлы/папки для исключения из синхронизации
EXCLUDE_FILES=(
    ".git"
    ".gitignore"
    "__pycache__"
    "*.pyc"
    ".env"
    ".venv"
    "venv"
    "*.log"
    ".pytest_cache"
    ".mypy_cache"
    "node_modules"
    ".venv"
    "*.pyo"
    ".coverage"
    "htmlcov"
)

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
        print_warning "Проверьте SSH ключи: ssh-keygen -R zerodolg-server"
        exit 1
    fi
    print_status "SSH-соединение OK"
}

# Бэкап перед деплоем
create_backup() {
    print_info "Создание бэкапа на сервере..."
    ssh "$SERVER_SSH" "
    cd $SERVER_PATH &&
    [ -f .env ] && cp .env .env.backup.\$(date +%Y%m%d_%H%M%S) &&
    [ -f docker-compose.yml ] && cp docker-compose.yml docker-compose.yml.backup.\$(date +%Y%m%d_%H%M%S) &&
    echo 'Бэкап создан'
    " || print_warning "Не удалось создать бэкап"
}

# Откат при ошибке
rollback() {
    print_warning "Выполняется откат..."
    ssh "$SERVER_SSH" "
    cd $SERVER_PATH &&
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

# Синхронизация файлов с сервером (rsync)
sync_files_to_server() {
    print_info "Синхронизация файлов с сервером..."
    
    # Формируем список исключений
    local excludes=""
    for exclude in "${EXCLUDE_FILES[@]}"; do
        excludes="$excludes --exclude='$exclude'"
    done
    
    # Синхронизация через rsync
    rsync -avz --delete \
        $excludes \
        -e "ssh -o ConnectTimeout=10" \
        ./ \
        "$SERVER_SSH:$SERVER_PATH/" \
        | tee -a "$DEPLOY_LOG"
    
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        print_status "Файлы синхронизированы"
    else
        print_error "Синхронизация не удалась!"
        exit 1
    fi
}

# Альтернатива через scp (если нет rsync)
sync_files_via_scp() {
    print_info "Синхронизация файлов через scp..."
    
    # Создаём временный архив
    local temp_archive="/tmp/deploy-$(date +%Y%m%d_%H%M%S).tar.gz"
    
    # Формируем команду tar с исключениями
    local tar_excludes=""
    for exclude in "${EXCLUDE_FILES[@]}"; do
        tar_excludes="$tar_excludes --exclude='$exclude'"
    done
    
    # Архивируем без исключений
    tar $tar_excludes -czf "$temp_archive" .
    
    # Копируем на сервер
    print_info "Копирование архива на сервер..."
    scp "$temp_archive" "$SERVER_SSH:/tmp/"
    
    # Распаковываем на сервере
    ssh "$SERVER_SSH" "
    cd $SERVER_PATH &&
    tar -xzf /tmp/deploy-*.tar.gz &&
    rm /tmp/deploy-*.tar.gz
    "
    
    # Удаляем локальный архив
    rm -f "$temp_archive"
    
    print_status "Файлы синхронизированы"
}

# Проверка зависимостей
check_dependencies() {
    print_info "Проверка зависимостей..."
    
    local missing=()
    
    # Проверка rsync
    if ! command -v rsync &> /dev/null; then
        missing+=("rsync")
    fi
    
    # Проверка ssh
    if ! command -v ssh &> /dev/null; then
        missing+=("ssh")
    fi
    
    if [ ${#missing[@]} -gt 0 ]; then
        print_error "Отсутствуют зависимости: ${missing[*]}"
        print_warning "Установите: sudo apt install ${missing[*]}"
        exit 1
    fi
    
    print_status "Все зависимости установлены"
}

# Основная функция деплоя
deploy_from_local() {
    print_info "Деплой с локальной машины на сервер ${SERVER_SSH}:${SERVER_PATH}..."
    echo "" | tee -a "$DEPLOY_LOG"
    
    # 0. Проверка SSH
    check_ssh_connection
    echo ""
    
    # 1. Бэкап
    create_backup
    echo ""
    
    # 2. Синхронизация файлов
    if command -v rsync &> /dev/null; then
        sync_files_to_server
    else
        print_warning "rsync не найден, используем scp..."
        sync_files_via_scp
    fi
    echo ""
    
    # 3. Проверка .env
    print_status "1. Проверка .env..."
    if ! ssh "$SERVER_SSH" "[ -f $SERVER_PATH/.env ]"; then
        print_error ".env файл не найден на сервере!"
        print_warning "Создайте .env на сервере или скопируйте вручную"
        rollback
        exit 1
    fi
    
    # 4. Пересборка Docker образов БЕЗ КЭША
    print_status "2. Пересборка Docker образов (без кэша)..."
    print_warning "Это может занять 5-15 минут..."
    if ! ssh "$SERVER_SSH" "
    cd $SERVER_PATH &&
    docker compose build --no-cache --pull ${SERVICES_TO_REBUILD[*]}
    "; then
        print_error "Docker build failed!"
        rollback
        exit 1
    fi
    
    # 5. Применение миграций
    print_status "3. Применение миграций..."
    if ! ssh "$SERVER_SSH" "
    cd $SERVER_PATH &&
    docker compose run --rm bot poetry run alembic upgrade head
    "; then
        print_error "Миграции failed!"
        rollback
        exit 1
    fi
    
    # 6. Остановка старых контейнеров
    print_status "4. Остановка старых контейнеров..."
    ssh "$SERVER_SSH" "
    cd $SERVER_PATH &&
    docker compose stop ${SERVICES_TO_REBUILD[*]}
    "
    
    # 7. Запуск обновлённых сервисов
    print_status "5. Запуск обновлённых сервисов..."
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
    print_status "6. Статус всех контейнеров..."
    ssh "$SERVER_SSH" "
    cd $SERVER_PATH &&
    docker compose ps
    "
    
    # 11. Очистка старых образов
    print_status "7. Очистка старых образов..."
    ssh "$SERVER_SSH" "
    cd $SERVER_PATH &&
    docker image prune -f --filter 'until=24h'
    "
    
    echo ""
    print_status "Деплой с локальной машины завершён успешно!"
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
echo "║     Market Bot — Деплой с локальной машина                ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Инициализация логирования
exec > >(tee -a "$DEPLOY_LOG") 2>&1

check_dependencies

check_ssh_connection

# Проверка текущей директории
if [ ! -f "docker-compose.yml" ]; then
    print_error "docker-compose.yml не найден в текущей директории!"
    print_warning "Запускайте скрипт из корня проекта"
    exit 1
fi

echo ""
print_warning "Внимание! Будет выполнен деплой с локального кода:"
echo "  Сервер: $SERVER_SSH"
echo "  Путь: $SERVER_PATH"
echo "  Сервисы: ${SERVICES_TO_REBUILD[*]}"
echo "  Режим: BUILD --no-cache (без кэша)"
echo "  Лог: $DEPLOY_LOG"
echo ""
print_warning "⚠ Пересборка без кэша может занять 5-15 минут!"
echo ""

read -p "Продолжить деплой? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_warning "Деплой отменён"
    exit 0
fi

deploy_from_local
show_logs

echo ""
print_status "Готово!"
print_info "Лог сохранён: $DEPLOY_LOG"
