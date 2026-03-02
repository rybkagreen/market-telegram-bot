@echo off
REM Cloudflare Tunnel with Named Tunnel (stable)

echo ============================================
echo   Cloudflare Tunnel for Market Bot
echo   (Named Tunnel - Stable)
echo ============================================
echo.

REM Check if config exists
if not exist "%~dp0cloudflared-config.yml" (
    echo ERROR: cloudflared-config.yml not found!
    echo.
    echo Run these commands first:
    echo   1. cloudflared.exe tunnel login
    echo   2. cloudflared.exe tunnel create market-bot
    echo   3. Edit cloudflared-config.yml with your tunnel ID
    echo.
    pause
    exit /b 1
)

echo Starting tunnel...
echo.
echo DO NOT CLOSE THIS WINDOW!
echo.

"C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --config "%~dp0cloudflared-config.yml" run market-bot

pause
