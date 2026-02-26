# 🔒 SECURITY ACTION REQUIRED — Скомпрометированный BOT_TOKEN

## Статус: ✅ Исправлено в коде, ⚠️ Требуется действие разработчика

---

## Что произошло

В коммите `8ca981f` (AUDIT_REPORT) был обнаружен хардкод реального BOT_TOKEN в файле `docker-compose.yml`:

```yaml
BOT_TOKEN: 7562867307:AAEIzuEqqRDV0kixpFHXIpVDgxaq0Xq_F_k  # ❌ REVOKE THIS!
```

В коммите `5179b6f` токен заменён на переменную окружения:

```yaml
BOT_TOKEN: ${BOT_TOKEN}  # ✅ Безопасно
```

**НО:** Токен мог остаться в истории git и быть загружен в remote repository.

---

## 🚨 Немедленные действия (P0)

### Шаг 1: Отозвать текущий токен

1. Открой @BotFather в Telegram
2. Отправь команду: `/mybots`
3. Выбери своего бота
4. Нажми `API Token`
5. Нажми `Revoke current token`

**⚠️ После этого старый токен перестанет работать!**

---

### Шаг 2: Получить новый токен

1. В @BotFather нажми `Create a new bot` или выбери существующего
2. Скопируй новый токен (выглядит как `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

---

### Шаг 3: Обновить .env локально

```bash
# Открой .env и замени:
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz  # Новый токен

# Также проверь что API_ID и API_HASH установлены:
API_ID=12345678  # Получи на my.telegram.org
API_HASH=abcdef1234567890abcdef1234567890  # Получи на my.telegram.org
```

---

### Шаг 4: Обновить .env на production сервере

```bash
# На сервере (timeweb.cloud):
cd /path/to/market-telegram-bot
nano .env  # Или vim/nano

# Обнови BOT_TOKEN на новый
# Сохрани файл

# Перезапусти контейнеры:
docker compose restart bot worker celery_beat
```

---

## 🧹 Очистка истории git (критично!)

Токен присутствовал в истории git до коммита `5179b6f`.

### Если ещё не пушили в remote:

```bash
# Уже выполнено в локальной ветке:
# - filter-branch переписал историю
# - gc очистил старые объекты

# Проверь что токен удалён:
git log -p -- docker-compose.yml | grep "7562867307"
# Должно быть пусто

# Пуш с force (история переписана!):
git push origin developer2/belin --force
```

### Если уже пушили в remote:

```bash
# 1. Очисти локальную историю (если ещё не сделано):
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# 2. Проверь что токен удалён локально:
git log -p -- docker-compose.yml | grep "7562867307"  # Пусто?

# 3. Force push в remote:
git push origin developer2/belin --force

# ⚠️ WARNING: Это перезапишет историю на remote!
```

---

## 📢 Уведомление команды

После force push все разработчики должны:

```bash
# Удалить локальную ветку:
git branch -D developer2/belin

# Заново checkout с remote:
git fetch origin
git checkout developer2/belin
git pull origin developer2/belin
```

---

## ✅ Проверка

### 1. Токен отозван?
- [ ] Старый токен не работает (бот не отвечает)
- [ ] Новый токен получен и записан в .env

### 2. История очищена?
```bash
# Эта команда должна вернуть пустой результат:
git log --all -p -- docker-compose.yml | grep "7562867307"
```

### 3. Remote обновлён?
```bash
# Проверь на GitHub/GitLab:
# - Открой docker-compose.yml в веб-интерфейсе
# - Убедись что BOT_TOKEN: ${BOT_TOKEN}
# - Проверь историю коммитов — старого токена нет
```

---

## 📝 Timeline

| Дата | Событие | Статус |
|------|---------|--------|
| 2026-02-26 | Обнаружен токен в AUDIT_REPORT | ✅ |
| 2026-02-26 | Токен заменён на ${BOT_TOKEN} | ✅ |
| 2026-02-26 | История переписана (filter-branch) | ✅ |
| 2026-02-26 | **Требуется:** Отозвать токен | ⏳ |
| 2026-02-26 | **Требуется:** Обновить .env | ⏳ |
| 2026-02-26 | **Требуется:** Force push | ⏳ |

---

## 🔗 Полезные ссылки

- [Telegram BotFather](https://t.me/BotFather)
- [Telegram API — my.telegram.org](https://my.telegram.org)
- [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/) — альтернатива filter-branch
- [GitHub — Removing sensitive data](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)

---

## Контакты

По вопросам безопасности обращаться:
- GitHub Issues (конфиденциально)
- Email: security@example.com
