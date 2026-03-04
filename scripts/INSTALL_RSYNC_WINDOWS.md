# 📦 Установка rsync для Windows

## Способ 1: Через winget (рекомендуется)

```powershell
# Открыть PowerShell от имени администратора
winget install GnuWin32.Rsync
```

## Способ 2: Ручная установка

### Шаг 1: Скачать rsync

Перейдите на сайт и скачайте архив:
- **Ссылка:** https://www.itefix.net/cwrsync
- **Или:** https://github.com/lukeshu/cwrsync/releases

### Шаг 2: Распаковать

1. Создайте папку: `C:\tools\rsync`
2. Распакуйте архив в эту папку
3. Найдите `rsync.exe` (обычно в `bin\rsync.exe`)

### Шаг 3: Добавить в PATH

#### Для PowerShell (от имени администратора):
```powershell
$envPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
$newPath = "C:\tools\rsync\bin;$envPath"
[Environment]::SetEnvironmentVariable("Path", $newPath, "Machine")
```

#### Для текущего пользователя:
```powershell
$envPath = [Environment]::GetEnvironmentVariable("Path", "User")
$newPath = "C:\tools\rsync\bin;$envPath"
[Environment]::SetEnvironmentVariable("Path", $newPath, "User")
```

### Шаг 4: Проверка

```powershell
# В PowerShell
rsync --version

# В Git Bash
rsync --version
```

---

## 🚀 Альтернатива: Использовать Git Bash rsync

Если установлен Git for Windows, rsync уже есть!

**Путь:** `C:\Program Files\Git\usr\bin\rsync.exe`

### Добавить в PATH:

```powershell
# PowerShell
$gitRsync = "C:\Program Files\Git\usr\bin"
$envPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($envPath -notlike "*$gitRsync*") {
    [Environment]::SetEnvironmentVariable("Path", "$gitRsync;$envPath", "User")
}
```

---

## ✅ Проверка установки

```powershell
# PowerShell
rsync --version

# Должно вывести:
# rsync  version 6.x.x  ...
```

---

## 🔧 Использование в VSCode

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

1. **Перезапустите терминал** после добавления в PATH
2. **Перезапустите VSCode** для применения изменений
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
2. Или установите в пользовательскую папку: `C:\Users\alex_\rsync`

---

## 📚 Ссылки

- Официальный сайт: https://www.itefix.net/cwrsync
- Документация: https://rsync.samba.org/documentation.html
- Git for Windows: https://git-scm.com/download/win
