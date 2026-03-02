# ══════════════════════════════════════════════════════════════
# Запуск Cloudflare Tunnel для Market Bot
# ══════════════════════════════════════════════════════════════

Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Запуск Cloudflare Tunnel" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Находим cloudflared через winget
Write-Host "[1/3] Поиск cloudflared..." -ForegroundColor Yellow
$cloudflaredPath = $null

# Пробуем стандартные пути
$possiblePaths = @(
    "$env:LOCALAPPDATA\Programs\cloudflared\cloudflared.exe",
    "$env:USERPROFILE\cloudflared.exe",
    "$env:PROGRAMFILES\cloudflared\cloudflared.exe",
    "C:\cloudflared.exe"
)

foreach ($path in $possiblePaths) {
    if (Test-Path $path) {
        $cloudflaredPath = $path
        Write-Host "  ✓ Найден: $cloudflaredPath" -ForegroundColor Green
        break
    }
}

# Если не нашли - пробуем через winget
if (-not $cloudflaredPath) {
    Write-Host "  Поиск через winget..." -ForegroundColor Gray
    $wingetInfo = winget list cloudflared 2>$null | Select-String "cloudflare"
    if ($wingetInfo) {
        Write-Host "  ✓ cloudflared установлен через winget" -ForegroundColor Green
        Write-Host "  Запускаю через winget exec..." -ForegroundColor Gray
        $cloudflaredPath = "winget"
    } else {
        Write-Host "  ✗ cloudflared не найден!" -ForegroundColor Red
        Write-Host ""
        Write-Host "  Установите: winget install cloudflare.cloudflared" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host ""

# Запуск туннеля
Write-Host "[2/3] Запуск туннеля к localhost:8080..." -ForegroundColor Yellow
Write-Host "  ╔═══════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "  ║  НЕ ЗАКРЫВАЙТЕ ЭТО ОКНО!                              ║" -ForegroundColor Cyan
Write-Host "  ║  Туннель должен работать пока вы пользуетесь ботом.   ║" -ForegroundColor Cyan
Write-Host "  ╚═══════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

if ($cloudflaredPath -eq "winget") {
    # Запуск через winget exec
    & winget exec cloudflare.cloudflared tunnel --url http://localhost:8080
} else {
    # Запуск напрямую
    & $cloudflaredPath tunnel --url http://localhost:8080
}
