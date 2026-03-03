#!/bin/bash
# Market Bot — Deploy Script
# Автоматическое обновление production сервера

set -e

echo "🚀 Market Bot — Deploy Script"
echo "=============================="
echo ""

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функция для печати статуса
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Проверка .env файла
print_status "Проверка .env..."
if [ ! -f .env ]; then
    print_error ".env файл не найден!"
    exit 1
fi

# Проверка Docker
print_status "Проверка Docker..."
if ! command -v docker &> /dev/null; then
    print_error "Docker не установлен!"
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    print_error "Docker Compose не установлен!"
    exit 1
fi

# Проверка running контейнеров
print_status "Текущий статус контейнеров..."
docker compose ps

# Backup данных (опционально)
print_warning "Создание backup (рекомендуется)..."
# docker compose exec postgres pg_dump -U market_bot market_bot_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Pull новых образов
print_status "Pull новых образов..."
docker compose pull

# Обновление сервисов (данные сохраняются!)
print_status "Обновление сервисов..."
docker compose up -d --no-deps bot api worker celery_beat flower

# Ожидание запуска
print_status "Ожидание запуска сервисов (10 сек)..."
sleep 10

# Применение миграций
print_status "Применение миграций..."
docker compose run --rm bot poetry run alembic upgrade head

# Проверка здоровья
print_status "Проверка здоровья сервисов..."
sleep 5
docker compose ps

# Проверка API
print_status "Проверка API health check..."
if curl -f http://localhost:8001/health > /dev/null 2>&1; then
    print_status "API health check: OK"
else
    print_warning "API health check: FAILED (возможно требуется больше времени)"
fi

# Проверка nginx
print_status "Проверка nginx health check..."
if curl -f http://localhost:8081/health > /dev/null 2>&1; then
    print_status "Nginx health check: OK"
else
    print_warning "Nginx health check: FAILED"
fi

# Очистка старых образов
print_status "Очистка старых образов..."
docker image prune -f

echo ""
echo "=============================="
print_status "Деплой завершён успешно!"
echo ""
echo "📊 Статус сервисов:"
docker compose ps --format "table {{.Name}}\t{{.Status}}"
echo ""
print_warning "Рекомендуется проверить логи: docker compose logs -f bot"
