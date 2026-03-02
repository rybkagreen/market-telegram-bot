# ══════════════════════════════════════════════════════════════
# Автоматическая настройка Cloudflare Tunnel для Market Bot
# ══════════════════════════════════════════════════════════════

Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Cloudflare Tunnel Setup для Market Bot" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Проверка cloudflared через winget
Write-Host "[1/4] Проверка cloudflared..." -ForegroundColor Yellow
$wingetCheck = winget list cloudflared 2>$null | Select-String "cloudflare"

if (-not $wingetCheck) {
    Write-Host "  ✗ cloudflared не установлен!" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Установка..." -ForegroundColor Yellow
    winget install -e --id cloudflare.cloudflared --silent --accept-package-agreements --accept-source-agreements 2>$null
    
    Start-Sleep -Seconds 3
    
    $wingetCheck = winget list cloudflared 2>$null | Select-String "cloudflare"
    if (-not $wingetCheck) {
        Write-Host "  ✗ Не удалось установить автоматически" -ForegroundColor Red
        Write-Host "  Установите вручную: winget install cloudflare.cloudflared" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host "  ✓ cloudflared установлен" -ForegroundColor Green
Write-Host ""

# Проверка что nginx работает на порту 8080
Write-Host "[2/4] Проверка Mini App на порту 8080..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri 'http://localhost:8080/app/' -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "  ✓ Mini App доступен на localhost:8080" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Mini App вернул статус: $($response.StatusCode)" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "  ✗ Mini App недоступен на localhost:8080" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Запустите: docker compose up -d nginx" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Запуск туннеля
Write-Host "[3/4] Запуск Cloudflare Tunnel..." -ForegroundColor Yellow
Write-Host ""
Write-Host "  ╔═══════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "  ║  Запускаю туннель в НОВОМ ОКНЕ PowerShell...          ║" -ForegroundColor Cyan
Write-Host "  ║                                                       ║" -ForegroundColor Cyan
Write-Host "  ║  ╨Э╨Х ╨Ч╨Р╨Ъ╨а╨л╨Т╨Р╨Щ╨в╨Х ╨н╤В╨╛ ╨╛╨║╨╜╨╛!                              ║" -ForegroundColor Red
Write-Host "  ║  ╨в╤Г╨╜╨╜╨╡╨╗╤М ╨┤╨╛╨╗╨╢╨╡╨╜ ╤А╨░╨▒╨╛╤В╨░╤В╤М ╨┐╨╛╨║╨░ ╨▓╤Л ╨┐╨╛╨╗╤М╨╖╤Г╨╡╤В╨╡╤Б╤П ╨▒╨╛╤В╨╛╨╝.     ║" -ForegroundColor Red
Write-Host "  ╚═══════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Создаём скрипт для запуска в новом окне
$tunnelScript = @"
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Cloudflare Tunnel для Market Bot" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Запуск туннеля..." -ForegroundColor Yellow
Write-Host ""

# Запускаем туннель
$env:PATH = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
winget exec cloudflare.cloudflared tunnel --url http://localhost:8080
"@

$tunnelScriptPath = Join-Path $PSScriptRoot "cloudflared-tunnel.ps1"
$tunnelScript | Out-File -FilePath $tunnelScriptPath -Encoding UTF8 -Force

# Запускаем в новом окне
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $tunnelScriptPath -WindowStyle Normal

Write-Host "  ✓ Туннель запущен в новом окне" -ForegroundColor Green
Write-Host ""
Write-Host "  Ожидание получения URL (до 15 секунд)..." -ForegroundColor Gray

# Ждём пока туннель получит URL
Start-Sleep -Seconds 8

Write-Host ""
Write-Host "[4/4] Настройка URL..." -ForegroundColor Yellow
Write-Host ""
Write-Host "  ╔═══════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "  ║  ╨Я╨Х╨а╨Х╨Щ╨Ф╨Ш╨в╨Х ╨▓ ╨╛╨║╨╜╨╛ ╤Б ╤В╤Г╨╜╨╜╨╡╨╗╨╡╨╝!                        ║" -ForegroundColor Yellow
Write-Host "  ║                                                       ║" -ForegroundColor Cyan
Write-Host "  ║  ╨▓╤Л ╤Г╨▓╨╕╨┤╨╕╤В╨╡ URL ╨▓╨╕╨┤╨░:                          ║" -ForegroundColor Cyan
Write-Host "  ║  https://xxxx-xxxx-xxxx.trycloudflare.com            ║" -ForegroundColor White
Write-Host "  ║                                                       ║" -ForegroundColor Cyan
Write-Host "  ║  ╨б╨║╨╛╨Я╨Ш╨а╨г╨Щ╨в╨Х ╤Н╤В╨╛╤В URL (╨▓╤Б╤О ╤Б╤Б╤Л╨╗╨║╤Г ╤Ж╨╡╨╗╨╕╨║╨╛╨╝)!          ║" -ForegroundColor Red
Write-Host "  ║  ╨Я╨Х╨а╨Х╨Щ╨Ф╨Ш╨в╨Х ╨╛╨▒╤А╨░╤В╨╜╨╛ ╨▓ ╤Н╤В╨╛ ╨╛╨║╨╜╨╛ ╨╕ ╨▓╤Б╤В╨░╨▓╤М╤В╨Х URL.       ║" -ForegroundColor Red
Write-Host "  ╚═══════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$miniAppUrl = Read-Host "  ╨Т╤Б╤В╨░╨▓╤М╤В╨╡ ╤Б╨║╨╛╨┐╨╕╤А╨╛╨▓╨░╨╜╨╜╤Л╨╣ URL (╨▒╨╡╨╖ /app ╨╜╨░ ╨║╨╛╨╜╤Ж╨╡)"

if ([string]::IsNullOrWhiteSpace($miniAppUrl)) {
    Write-Host "  ✗ URL ╨╜╨╡ ╨▓╨▓╨╡╨┤╤С╨╜!" -ForegroundColor Red
    Write-Host ""
    Write-Host "  ╨Ч╨░╨┐╤Г╤Б╤В╨╕╤В╨╡ ╤Б╨║╤А╨╕╨┐╤В ╤Б╨╜╨╛╨▓╨░: .\scripts\setup-cloudflared.ps1" -ForegroundColor Yellow
    exit 1
}

# ╨г╨┤╨░╨╗╤П╨╡╨╝ trailing slash ╨╡╤Б╨╗╨╕ ╨╡╤Б╤В╤М
$miniAppUrl = $miniAppUrl.TrimEnd('/')

Write-Host "  ✓ URL ╨┐╤А╨╕╨╜╤П╤В: $miniAppUrl" -ForegroundColor Green
Write-Host ""

# ╨Ю╨▒╨╜╨╛╨▓╨╗╤П╨╡╨╝ .env
Write-Host "  ╨Ю╨▒╨╜╨╛╨▓╨╗╨╡╨╜╨╕╨╡ .env..." -ForegroundColor Yellow

$envPath = Join-Path $PSScriptRoot "..\.env"

if (Test-Path $envPath) {
    $envContent = Get-Content $envPath -Raw
    $envContent = $envContent -replace 'MINI_APP_URL=.*', "MINI_APP_URL=$miniAppUrl/app"
    $envContent | Out-File -FilePath $envPath -Encoding UTF8 -Force
    Write-Host "  ✓ .env ╨╛╨▒╨╜╨╛╨▓╨╗╤С╨╜" -ForegroundColor Green
} else {
    Write-Host "  ✗ .env ╨╜╨╡ ╨╜╨░╨╣╨┤╨╡╨╜!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "  ╨Э╨░╤Б╤В╤А╨╛╨╣╨║╨░ ╨╖╨░╨▓╨╡╤А╤И╨╡╨╜╨░!" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Host "╨б╨╗╨╡╨┤╤Г╤О╤Й╨╕╨╡ ╤И╨░╨│╨╕:" -ForegroundColor Yellow
Write-Host "  1. ╨Я╨╡╤А╨╡╨╖╨░╨┐╤Г╤Б╤В╨╕╤В╨╡ ╨▒╨╛╤В╨░:" -ForegroundColor White
Write-Host "     docker compose restart bot" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. ╨Ю╤В╨║╤А╨╛╨╣╤В╨╡ Telegram: @Eliza_rybka_assistant_bot" -ForegroundColor White
Write-Host ""
Write-Host "  3. ╨Э╨░╨╢╨╝╨╕╤В╨╡ /start ╨╕ ╨║╨╜╨╛╨┐╨║╤Г '📱 ╨Ю╤В╨║╤А╤Л╤В╤М ╨║╨░╨▒╨╕╨╜╨╡╤В'" -ForegroundColor White
Write-Host ""
Write-Host "╨Ю╨║╨╜╨╛ ╤Б ╤В╤Г╨╜╨╜╨╡╨╗╨╡╨╝ ╨┤╨╛╨╗╨╢╨╜╨╛ ╨╛╤Б╤В╨░╨▓╨░╤В╤М╤Б╤П ╨╛╤В╨║╤А╤Л╤В╤Л╨╝!" -ForegroundColor Red
Write-Host ""
