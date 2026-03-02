# Cloudflare Tunnel Auto Setup for Market Bot
# cloudflared location: C:\Program Files (x86)\cloudflared\cloudflared.exe

param([switch]$SkipBotRestart)

$CLOUDFLARED_PATH = "C:\Program Files (x86)\cloudflared\cloudflared.exe"

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  Cloudflare Tunnel - Auto Setup" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check cloudflared
Write-Host "[1/5] Checking cloudflared..." -ForegroundColor Yellow
if (Test-Path $CLOUDFLARED_PATH) {
    Write-Host "  OK: cloudflared found at $CLOUDFLARED_PATH" -ForegroundColor Green
} else {
    Write-Host "  ERROR: cloudflared not found at $CLOUDFLARED_PATH" -ForegroundColor Red
    Write-Host "  Installing..." -ForegroundColor Gray
    winget install -e --id cloudflare.cloudflared --silent --accept-package-agreements --accept-source-agreements 2>$null
    Start-Sleep -Seconds 5
    
    if (-not (Test-Path $CLOUDFLARED_PATH)) {
        Write-Host "  ERROR: Installation failed" -ForegroundColor Red
        exit 1
    }
}
Write-Host ""

# Add to PATH
$env:Path = "$CLOUDFLARED_PATH\..;" + $env:Path

# Step 2: Check Mini App
Write-Host "[2/5] Checking Mini App..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri 'http://localhost:8080/app/' -TimeoutSec 5 -UseBasicParsing
    Write-Host "  OK: Mini App running on localhost:8080" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Mini App not available!" -ForegroundColor Red
    Write-Host "  Run: docker compose up -d nginx" -ForegroundColor Yellow
    exit 1
}
Write-Host ""

# Step 3: Start tunnel
Write-Host "[3/5] Starting Cloudflare Tunnel..." -ForegroundColor Yellow
Write-Host "  Launching tunnel in new window..." -ForegroundColor Gray

$tunnelScript = @"
Write-Host 'Starting Cloudflare Tunnel...' -ForegroundColor Yellow
Write-Host ''
Write-Host 'DO NOT CLOSE THIS WINDOW!' -ForegroundColor Red
Write-Host 'Keep this open while using the bot.' -ForegroundColor Red
Write-Host ''
Write-Host 'Using HTTP/2 protocol for better stability.' -ForegroundColor Cyan
Write-Host ''
& '$CLOUDFLARED_PATH' tunnel --protocol http2 --url http://localhost:8080
"@

$tunnelScriptPath = "$env:TEMP\start-cloudflared.ps1"
$tunnelScript | Out-File -FilePath $tunnelScriptPath -Encoding UTF8 -Force

# Launch tunnel in new window
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $tunnelScriptPath

Write-Host "  OK: Tunnel starting in new window" -ForegroundColor Green
Write-Host ""
Write-Host "  ╔═══════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "  ║  ПЕРЕЙДИТЕ в окно туннеля!                            ║" -ForegroundColor Yellow
Write-Host "  ║                                                       ║" -ForegroundColor Cyan
Write-Host "  ║  Вы увидите URL вида:                                 ║" -ForegroundColor Cyan
Write-Host "  ║  https://xxxx-xxxx-xxxx.trycloudflare.com            ║" -ForegroundColor White
Write-Host "  ║                                                       ║" -ForegroundColor Cyan
Write-Host "  ║  СКОПИРУЙТЕ этот URL (всю ссылку)!                    ║" -ForegroundColor Red
Write-Host "  ║  ПЕРЕЙДИТЕ обратно в это окно и вставьте URL.         ║" -ForegroundColor Red
Write-Host "  ╚═══════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$tunnelUrl = Read-Host "  Вставьте скопированный URL (без /app на конце)"

if ([string]::IsNullOrWhiteSpace($tunnelUrl)) {
    Write-Host "  ERROR: No URL provided!" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Run the script again: .\scripts\setup-cloudflared-auto.ps1" -ForegroundColor Yellow
    exit 1
}

$tunnelUrl = $tunnelUrl.TrimEnd('/')
Write-Host "  OK: URL accepted: $tunnelUrl" -ForegroundColor Green
Write-Host ""

# Step 4: Update .env
Write-Host "[4/5] Updating .env..." -ForegroundColor Yellow

$envPath = Join-Path $PSScriptRoot "..\.env"
if (Test-Path $envPath) {
    $envContent = Get-Content $envPath -Raw
    $envContent = $envContent -replace 'MINI_APP_URL=.*', "MINI_APP_URL=$tunnelUrl/app"
    $envContent | Out-File -FilePath $envPath -Encoding UTF8 -Force
    Write-Host "  OK: .env updated" -ForegroundColor Green
} else {
    Write-Host "  ERROR: .env not found!" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 5: Restart bot
Write-Host "[5/5] Restarting bot..." -ForegroundColor Yellow
if (-not $SkipBotRestart) {
    docker compose restart bot 2>$null
    Write-Host "  OK: Bot restarted" -ForegroundColor Green
} else {
    Write-Host "  SKIPPED: Use -SkipBotRestart flag" -ForegroundColor Gray
}
Write-Host ""

# Done
Write-Host "=============================================" -ForegroundColor Green
Write-Host "  DONE!" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Mini App available at HTTPS:" -ForegroundColor Cyan
Write-Host "  $tunnelUrl/app" -ForegroundColor White
Write-Host ""
Write-Host "Telegram bot: @Eliza_rybka_assistant_bot" -ForegroundColor Cyan
Write-Host ""
Write-Host "IMPORTANT: Keep the tunnel window OPEN!" -ForegroundColor Red
Write-Host ""
