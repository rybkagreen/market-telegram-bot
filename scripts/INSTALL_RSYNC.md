# 📦 Быстрая установка rsync для Windows

## ✅ Способ 1: Использовать Git Bash (уже установлен!)

Если у вас установлен Git for Windows, rsync уже есть в системе!

**Путь:** `C:\Program Files\Git\usr\bin\rsync.exe`

### Добавить в PATH (PowerShell):

```powershell
# Добавить Git usr/bin в PATH пользователя
$gitPath = "C:\Program Files\Git\usr\bin"
$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")

if ($currentPath -notlike "*$gitPath*") {
    [Environment]::SetEnvironmentVariable("Path", "$gitPath;$currentPath", "User")
    Write-Host "✓ Git usr/bin добавлен в PATH" -ForegroundColor Green
    Write-Host "⚠ Перезапустите терминал для применения изменений" -ForegroundColor Yellow
}
```

### Проверка:

```powershell
# PowerShell
rsync --version

# Git Bash
rsync --version
```

---

## ✅ Способ 2: Ручная загрузка cwrsync

### Шаг 1: Скачать

Перейдите на сайт и скачайте последнюю версию:
- **https://www.itefix.net/cwrsync**
- Нажмите "Download cwrsync"

### Шаг 2: Распаковать

1. Создайте папку: `C:\tools\rsync`
2. Распакуйте содержимое архива в эту папку

### Шаг 3: Добавить в PATH

```powershell
# От имени администратора
$rsyncPath = "C:\tools\rsync\bin"
$currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")

if ($currentPath -notlike "*$rsyncPath*") {
    [Environment]::SetEnvironmentVariable("Path", "$rsyncPath;$currentPath", "Machine")
    Write-Host "✓ rsync добавлен в системный PATH" -ForegroundColor Green
}
```

---

## ✅ Способ 3: Через Chocolatey (если установлен)

```powershell
# От имени администратора
choco install rsync -y
```

---

## 🔧 Проверка установки

```powershell
# PowerShell
rsync --version

# Должно вывести:
# rsync  version 6.x.x  protocol version 31
```

---

## 🚀 Использование в VSCode

### PowerShell терминал:
```powershell
cd c:\Users\alex_\python-projects\market-telegram-bot
rsync -avz ./ src/bot/
```

### Git Bash терминал:
```bash
cd /c/Users/alex_/python-projects/market-telegram-bot
rsync -avz ./ src/bot/
```

---

## 📝 Примечания

1. **Перезапустите VSCode** после добавления в PATH
2. **Перезапустите терминал** для применения изменений
3. Если rsync не найден, проверьте PATH:
   ```powershell
   $env:Path -split ';' | Select-String rsync
   ```

---

## 🆘 Troubleshooting

### Ошибка: "rsync: command not found"

**Решение:**
1. Проверьте установку: `where rsync` (PowerShell)
2. Перезапустите терминал
3. Проверьте PATH: `$env:Path`

### Ошибка: "permission denied"

**Решение:**
1. Запустите PowerShell от имени администратора
2. Или установите в пользовательскую папку

---

## 📚 Ссылки

- cwrsync: https://www.itefix.net/cwrsync
- Git for Windows: https://git-scm.com/download/win
- rsync документация: https://rsync.samba.org/documentation.html
