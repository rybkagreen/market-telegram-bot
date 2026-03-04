#!/bin/bash
# Market Bot — Скрипт обновления с пересборкой Docker-контейнеров
# Использование: ./scripts/deploy-from-local.sh
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

# Критические сервисы — деплой провалится если они не поднялись
CRITICAL_SERVICES=("bot" "api" "worker" "celery_beat" "nginx")

# ══════════════════════════════════════════════════════════════
# ЦВЕТА
# ══════════════════════════════════════════════════════════════
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ══════════════════════════════════════════════════════════════
# ЛОГИРОВАНИЕ — инициализируем сразу, до всех вызовов функций
# ══════════════════════════════════════════════════════════════
exec > >(tee -a "$DEPLOY_LOG") 2>&1

# ══════════════════════════════════════════════════════════════
# ФУНКЦИИ
# ══════════════════════════════════════════════════════════════

print_status()  { echo -e "${GREEN}✓${NC} $1"; }
print_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
print_error()   { echo -e "${RED}✗${NC} $1"; }
print_info()    { echo -e "${BLUE}ℹ${NC} $1"; }
print_step()    { echo -e "\n${BLUE}━━━ $1 ━━━${NC}"; }

# ──────────────────────────────────────────────────────────────
# Проверка SSH
# ──────────────────────────────────────────────────────────────
check_ssh_connection() {
    print_info "Проверка SSH-соединения с $SERVER_SSH..."
    if ! ssh -o ConnectTimeout=10 -o BatchMode=yes "$SERVER_SSH" "exit" 2>/dev/null; then
        print_error "Не удалось подключиться к серверу $SERVER_SSH!"
        print_info "Проверь ~/.ssh/config и доступность сервера."
        exit 1
    fi
    print_status "SSH-соединение OK"
}

# ──────────────────────────────────────────────────────────────
# Проверка локальных prerequisites
# ──────────────────────────────────────────────────────────────
check_prerequisites() {
    print_step "Проверка prerequisites"

    for cmd in git ssh; do
        if ! command -v "$cmd" &>/dev/null; then
            print_error "$cmd не установлен!"
            exit 1
        fi
    done

    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    if [ "$CURRENT_BRANCH" != "$LOCAL_BRANCH" ]; then
        print_warning "Текущая ветка: $CURRENT_BRANCH (ожидалась: $LOCAL_BRANCH)"
        read -p "Продолжить? (y/n): " -n 1 -r; echo
        [[ $REPLY =~ ^[Yy]$ ]] || exit 0
    fi

    if [ -n "$(git status --porcelain)" ]; then
        print_warning "Есть незакоммиченные изменения!"
        git status --short
        read -p "Продолжить? (y/n): " -n 1 -r; echo
        [[ $REPLY =~ ^[Yy]$ ]] || exit 0
    fi

    print_status "Prerequisites OK"
}

# ──────────────────────────────────────────────────────────────
# Бэкап перед обновлением
# ──────────────────────────────────────────────────────────────
create_backup() {
    print_step "Создание бэкапа"

    ssh "$SERVER_SSH" "
        set -e
        cd $SERVER_PATH

        # Бэкап .env
        if [ -f .env ]; then
            cp .env .env.backup.\$(date +%Y%m%d_%H%M%S)
            echo 'Бэкап .env создан'
        fi

        # Сохраняем текущий git HEAD для возможного отката
        git rev-parse HEAD > /tmp/market_bot_pre_deploy_head.txt
        echo \"Текущий HEAD: \$(cat /tmp/market_bot_pre_deploy_head.txt)\"

        # Сохраняем текущую ревизию Alembic — нужна для ручного отката миграций
        echo 'Текущая ревизия Alembic:'
        docker compose run --rm --no-deps bot \
            poetry run alembic current 2>/dev/null || echo 'alembic current: недоступно (первый деплой?)'
    " || print_warning "Бэкап выполнен частично — продолжаем"
}

# ──────────────────────────────────────────────────────────────
# Откат при критической ошибке
# ──────────────────────────────────────────────────────────────
rollback() {
    print_warning "Выполняется откат..."

    ssh "$SERVER_SSH" "
        set -e
        cd $SERVER_PATH

        # Останавливаем все пересобранные сервисы
        docker compose stop ${SERVICES_TO_REBUILD[*]} 2>/dev/null || true

        # Возвращаем предыдущий git HEAD
        if [ -f /tmp/market_bot_pre_deploy_head.txt ]; then
            PREV_HEAD=\$(cat /tmp/market_bot_pre_deploy_head.txt)
            git reset --hard \"\$PREV_HEAD\"
            echo \"Откат git к \$PREV_HEAD\"
        else
            git reset --hard HEAD~1 2>/dev/null || echo 'Нет коммитов для отката'
        fi

        # Запускаем сервисы с предыдущим кодом
        docker compose up -d ${SERVICES_TO_REBUILD[*]} 2>/dev/null || echo 'Откат Docker не выполнен'
    " || print_error "Откат завершился с ошибкой — требуется ручное вмешательство!"

    print_warning "Откат завершён. Проверь состояние сервера вручную."
    print_info "Лог деплоя: $DEPLOY_LOG"
}

# ──────────────────────────────────────────────────────────────
# Ожидание запуска сервиса
# ──────────────────────────────────────────────────────────────
wait_for_service() {
    local service=$1
    local max_attempts=30
    local attempt=1

    print_info "Ожидание запуска $service..."
    while [ $attempt -le $max_attempts ]; do
        if ssh "$SERVER_SSH" \
            "cd $SERVER_PATH && docker compose ps $service 2>/dev/null | grep -qE 'Up|running'"; then
            print_status "$service: запущен (попытка $attempt/$max_attempts)"
            return 0
        fi
        sleep 2
        attempt=$((attempt + 1))
    done

    print_error "$service: не запустился за $((max_attempts * 2))с!"

    # Показываем логи упавшего сервиса для диагностики
    print_info "Последние логи $service:"
    ssh "$SERVER_SSH" \
        "cd $SERVER_PATH && docker compose logs --tail=30 $service" || true

    return 1
}

# ──────────────────────────────────────────────────────────────
# Health check API
# ──────────────────────────────────────────────────────────────
health_check_api() {
    print_info "Health check API (http://localhost:8001/health)..."
    local max_attempts=15
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if ssh "$SERVER_SSH" "curl -sf http://localhost:8001/health" >/dev/null 2>&1; then
            print_status "API health check: OK"
            return 0
        fi
        sleep 2
        attempt=$((attempt + 1))
        print_info "Ожидание API... ($attempt/$max_attempts)"
    done

    print_warning "API health check: FAILED — API не ответил за $((max_attempts * 2))с"
    print_info "Проверь /health endpoint — возможно он не реализован или на другом порту"
    return 1
}

# ──────────────────────────────────────────────────────────────
# Graceful shutdown Celery workers
# ──────────────────────────────────────────────────────────────
graceful_celery_shutdown() {
    print_info "Graceful shutdown Celery workers (ждём завершения текущих задач)..."

    ssh "$SERVER_SSH" "
        cd $SERVER_PATH

        # Отправляем сигнал завершения — workers доделают текущие задачи
        docker compose exec -T worker \
            celery -A src.tasks.celery_app control shutdown 2>/dev/null \
            && echo 'Сигнал shutdown отправлен' \
            || echo 'Worker недоступен или уже остановлен'

        # Даём 10 секунд на завершение текущих задач
        sleep 10
    " || print_warning "Graceful shutdown не выполнен — принудительная остановка"
}

# ══════════════════════════════════════════════════════════════
# ОСНОВНАЯ ФУНКЦИЯ ДЕПЛОЯ
# ══════════════════════════════════════════════════════════════
rebuild_and_deploy() {
    print_info "Начало деплоя → ${SERVER_SSH}:${SERVER_PATH} [ветка: $LOCAL_BRANCH]"

    # ── 1. Git pull ───────────────────────────────────────────
    print_step "1. Получение изменений из репозитория"
    if ! ssh "$SERVER_SSH" "
        set -e
        cd $SERVER_PATH
        git fetch origin $LOCAL_BRANCH
        git checkout $LOCAL_BRANCH
        git reset --hard origin/$LOCAL_BRANCH
        echo \"HEAD после обновления: \$(git rev-parse --short HEAD)\"
        echo \"Последний коммит: \$(git log -1 --pretty='%h %s' HEAD)\"
    "; then
        print_error "Git pull failed!"
        rollback
        exit 1
    fi

    # ── 2. Проверка .env ──────────────────────────────────────
    print_step "2. Проверка .env"
    if ! ssh "$SERVER_SSH" "[ -f $SERVER_PATH/.env ]"; then
        print_error ".env файл не найден на сервере!"
        print_info "Создай $SERVER_PATH/.env по образцу .env.example"
        rollback
        exit 1
    fi
    print_status ".env найден"

    # ── 3. Пересборка Docker образов ──────────────────────────
    print_step "3. Пересборка Docker образов (без кэша)"
    print_warning "Это может занять 5–15 минут..."
    if ! ssh "$SERVER_SSH" "
        cd $SERVER_PATH
        docker compose build --no-cache --pull ${SERVICES_TO_REBUILD[*]}
    "; then
        print_error "Docker build failed!"
        rollback
        exit 1
    fi
    print_status "Docker образы пересобраны"

    # ── 4. Graceful shutdown Celery ───────────────────────────
    print_step "4. Graceful shutdown Celery workers"
    graceful_celery_shutdown

    # ── 5. Остановка старых контейнеров ──────────────────────
    print_step "5. Остановка старых контейнеров"
    ssh "$SERVER_SSH" "
        cd $SERVER_PATH
        docker compose stop ${SERVICES_TO_REBUILD[*]}
        echo 'Контейнеры остановлены'
    "

    # ── 6. Применение миграций ────────────────────────────────
    # ВАЖНО: после остановки старых контейнеров, до запуска новых.
    # Это исключает конфликт между старым кодом и новой схемой БД.
    print_step "6. Применение миграций Alembic"
    if ! ssh "$SERVER_SSH" "
        cd $SERVER_PATH
        echo 'Ревизия до миграции:'
        docker compose run --rm --no-deps bot poetry run alembic current

        echo 'Применяем миграции...'
        docker compose run --rm --no-deps bot poetry run alembic upgrade head

        echo 'Ревизия после миграции:'
        docker compose run --rm --no-deps bot poetry run alembic current
    "; then
        print_error "Миграции провалились!"
        print_warning "БД может быть в частично применённом состоянии."
        print_warning "Выполни ручной откат: alembic downgrade -1"
        # Не делаем автоматический rollback БД — это опасно
        rollback
        exit 1
    fi

    # ── 7. Запуск обновлённых сервисов ───────────────────────
    print_step "7. Запуск обновлённых сервисов"
    if ! ssh "$SERVER_SSH" "
        cd $SERVER_PATH
        docker compose up -d --no-deps ${SERVICES_TO_REBUILD[*]}
    "; then
        print_error "docker compose up failed!"
        rollback
        exit 1
    fi

    # ── 8. Ожидание критических сервисов ─────────────────────
    print_step "8. Проверка запуска критических сервисов"
    for service in "${CRITICAL_SERVICES[@]}"; do
        if ! wait_for_service "$service"; then
            print_error "Критический сервис $service не запустился!"
            rollback
            exit 1
        fi
    done

    # ── 9. Health check API ───────────────────────────────────
    print_step "9. Health check API"
    health_check_api || true  # Не критично — продолжаем даже при FAILED

    # ── 10. Статус всех контейнеров ──────────────────────────
    print_step "10. Статус всех контейнеров"
    ssh "$SERVER_SSH" "cd $SERVER_PATH && docker compose ps"

    # ── 11. Очистка старых образов ────────────────────────────
    print_step "11. Очистка устаревших Docker образов"
    ssh "$SERVER_SSH" "
        docker image prune -f --filter 'until=24h'
        echo 'Очистка завершена'
    "

    echo ""
    print_status "════════════════════════════════════════════"
    print_status " Деплой завершён успешно!"
    print_status "════════════════════════════════════════════"
}

# ──────────────────────────────────────────────────────────────
# Показать логи бота после деплоя
# ──────────────────────────────────────────────────────────────
show_logs() {
    echo ""
    read -p "Показать логи бота? (y/n): " -n 1 -r; echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Ctrl+C для выхода из логов"
        ssh "$SERVER_SSH" "cd $SERVER_PATH && docker compose logs -f --tail=50 bot"
    fi
}

# ══════════════════════════════════════════════════════════════
# ТОЧКА ВХОДА
# ══════════════════════════════════════════════════════════════

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║        Market Bot — Деплой с пересборкой Docker           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
print_info "Лог деплоя: $DEPLOY_LOG"
echo ""

check_prerequisites
check_ssh_connection

echo ""
print_warning "Параметры деплоя:"
echo "  Сервер:   $SERVER_SSH"
echo "  Путь:     $SERVER_PATH"
echo "  Ветка:    $LOCAL_BRANCH"
echo "  Сервисы:  ${SERVICES_TO_REBUILD[*]}"
echo "  Режим:    --no-cache (полная пересборка)"
echo ""
print_warning "⚠ Пересборка без кэша займёт 5–15 минут!"
print_warning "⚠ Бот будет недоступен во время деплоя!"
echo ""
read -p "Начать деплой? (y/n): " -n 1 -r; echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_warning "Деплой отменён"
    exit 0
fi

# Ловим ошибки — при неожиданном выходе показываем где упало
trap 'print_error "Скрипт прерван на строке $LINENO. Лог: $DEPLOY_LOG"' ERR

create_backup
rebuild_and_deploy
show_logs

echo ""
print_status "Готово! Лог сохранён: $DEPLOY_LOG"