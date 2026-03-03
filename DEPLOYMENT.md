# 🚀 Локальный деплой на Timeweb Cloud

Инструкция по развертыванию Market Telegram Bot на сервере **напрямую из локальной ветки main** без GitHub Actions.

---

## 📋 Быстрый старт

### 1. Настройка конфигурации

**Откройте `scripts/deploy-to-server.ps1`** и заполните:

```powershell
# Сервер Timeweb Cloud
$SERVER_HOST = "123.45.67.89"          # IP вашего сервера
$SERVER_PORT = "22"                     # SSH порт
$SERVER_USER = "root"                   # Пользователь
$SERVER_PATH = "/opt/market-telegram-bot"  # Путь к проекту

# Локальная ветка
$LOCAL_BRANCH = "main"                  # Ветка для деплоя
```

### 2. Подготовка SSH ключа

**Windows PowerShell (от администратора):**
```powershell
# Генерация ключа
ssh-keygen -t ed25519 -C "market-bot-deploy"

# Копирование на сервер
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh root@<SERVER_IP> "cat >> ~/.ssh/authorized_keys"

# Проверка подключения
ssh root@<SERVER_IP>
```

### 3. Первый деплой

**Из PowerShell:**
```powershell
cd c:\Users\alex_\python-projects\market-telegram-bot
.\scripts\deploy-to-server.ps1
```

**Или из Bash (Git Bash/WSL):**
```bash
cd /c/Users/alex_/python-projects/market-telegram-bot
bash scripts/deploy-to-server.sh
```

---

## 🔧 Подготовка сервера Timeweb Cloud

### 1. Подключение к серверу

```powershell
ssh root@<SERVER_IP> -p 22
```

### 2. Установка Docker

```bash
# Обновление
apt update && apt upgrade -y

# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Проверка
docker --version
docker compose version
```

### 3. Клонирование проекта

```bash
cd /opt
git clone https://github.com/rybkagreen/market-telegram-bot.git
cd market-telegram-bot
```

### 4. Настройка .env

```bash
cp .env.example .env
nano .env
```

**Заполните критические переменные:**
```env
# Telegram
BOT_TOKEN=your_bot_token_from_botfather
ADMIN_IDS=1333213303

# Database
DATABASE_URL=postgresql+asyncpg://market_bot:market_bot_pass@postgres:5432/market_bot_db
POSTGRES_USER=market_bot
POSTGRES_PASSWORD=market_bot_pass

# Redis
REDIS_URL=redis://redis:6379/0

# AI
OPENROUTER_API_KEY=sk-or-v1-your_key_here

# JWT (сгенерировать!)
# python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET=your_generated_secret_here
```

### 5. Первый запуск

```bash
# Запуск PostgreSQL и Redis
docker compose up -d postgres redis

# Ожидание
sleep 20

# Применение миграций
docker compose run --rm bot poetry run alembic upgrade head

# Запуск всех сервисов
docker compose up -d

# Проверка
docker compose ps
```

---

## 🌐 Настройка nginx с лэндингом

### Вариант A: Поддомен (рекомендуется)

**1. DNS в Timeweb:**
```
Тип: A
Имя: bot
Значение: <IP сервера>
TTL: 3600
```

**2. Конфигурация nginx:**
```bash
nano /etc/nginx/sites-available/market-bot
```

```nginx
server {
    listen 80;
    server_name bot.yourdomain.ru;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**3. Активация:**
```bash
ln -s /etc/nginx/sites-available/market-bot /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx
```

**4. HTTPS (рекомендуется):**
```bash
apt install certbot python3-certbot-nginx -y
certbot --nginx -d bot.yourdomain.ru
```

### Вариант B: Подпуть

```nginx
server {
    listen 80;
    server_name yourdomain.ru;

    # Лэндинг
    location / {
        root /var/www/landing;
        index index.html;
    }

    # Market Bot
    location /bot/ {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
    }
}
```

---

## 🔄 Процесс деплоя

### Автоматический скрипт

**Локально (PowerShell):**
```powershell
.\scripts\deploy-to-server.ps1
```

**Что делает скрипт:**
1. ✓ Проверка Git и SSH
2. ✓ Проверка текущей ветки (должна быть main)
3. ✓ Проверка незакоммиченных изменений
4. ✓ Git pull на сервере
5. ✓ Проверка .env
6. ✓ Docker pull образов
7. ✓ Применение миграций (alembic upgrade head)
8. ✓ Обновление сервисов (bot, api, worker, celery_beat)
9. ✓ Health check API
10. ✓ Очистка старых образов

### Ручной деплой

**Подключение к серверу:**
```powershell
ssh root@<SERVER_IP>
```

**Команды на сервере:**
```bash
cd /opt/market-telegram-bot

# Git pull
git pull origin main

# Pull образов
docker compose pull

# Миграции
docker compose run --rm bot poetry run alembic upgrade head

# Обновление сервисов
docker compose up -d --no-deps bot api worker celery_beat

# Проверка
docker compose ps
docker compose logs -f bot
```

---

## 💾 Сохранение данных

### Что сохраняется при обновлении:

| Данные | Где хранятся | Сохраняется? |
|--------|--------------|--------------|
| **PostgreSQL** | Docker volume | ✅ ДА |
| **Redis** | Docker volume | ✅ ДА |
| **.env файл** | На сервере | ✅ ДА |
| **Логи** | Docker logs | ✅ ДА |
| **Docker образы** | Docker registry | ✅ ДА |

### Проверка volumes:

```bash
# На сервере
docker volume ls | grep market-telegram-bot

# Проверка данных
docker compose exec postgres psql -U market_bot -c "SELECT COUNT(*) FROM users;"
```

### ⚠️ Чего НЕ делать:

```bash
# ❌ Удалит ВСЕ данные!
docker compose down --volumes

# ❌ Удалит проект
rm -rf /opt/market-telegram-bot
```

---

## 📊 Мониторинг после деплоя

### Логи

```bash
# Все сервисы
docker compose logs -f

# Только бот
docker compose logs -f bot

# Последние 50 строк
docker compose logs --tail=50 bot
```

### Статус сервисов

```bash
docker compose ps
```

### Health checks

```bash
# API
curl http://localhost:8001/health

# Nginx
curl http://localhost:8080/health

# Flower (Celery UI)
# Откройте: http://<SERVER_IP>:5555
```

### Тестирование бота

1. Откройте Telegram
2. Найдите вашего бота
3. Отправьте `/start`
4. Проверьте ответ

---

## 🛠️ Troubleshooting

### Бот не отвечает

```bash
# Проверка логов
docker compose logs bot

# Перезапуск
docker compose restart bot

# Проверка .env
docker compose exec bot cat .env | grep BOT_TOKEN
```

### Миграции не применяются

```bash
# Проверка текущей миграции
docker compose run --rm bot poetry run alembic current

# Принудительное применение
docker compose run --rm bot poetry run alembic upgrade head
```

### Nginx возвращает 502

```bash
# Проверка что Market Bot запущен
docker compose ps

# Проверка логов nginx
tail -f /var/log/nginx/error.log

# Перезапуск nginx
systemctl restart nginx
```

### Конфликт с лэндингом

**Проверка занятых портов:**
```bash
netstat -tulpn | grep :80
```

**Решение:** Используйте поддомен (Вариант A) или измените порт в nginx.

---

## 📝 Чек-лист после деплоя

- [ ] Скрипт `deploy-to-server.ps1` настроен
- [ ] SSH ключ скопирован на сервер
- [ ] Docker установлен на сервере
- [ ] .env файл заполнен
- [ ] Миграции применены
- [ ] Все сервисы запущены (`docker compose ps`)
- [ ] Бот отвечает на `/start`
- [ ] Админ-панель доступна (`/admin`)
- [ ] nginx настроен (поддомен или подпуть)
- [ ] HTTPS настроен (certbot)

---

## 📞 Поддержка

При проблемах:
1. Проверьте логи: `docker compose logs -f`
2. Проверьте статус: `docker compose ps`
3. Проверьте nginx: `nginx -t`

**Документация:**
- [Docker Compose](https://docs.docker.com/compose/)
- [Alembic](https://alembic.sqlalchemy.org/)
- [Timeweb Cloud](https://timeweb.cloud/docs)
