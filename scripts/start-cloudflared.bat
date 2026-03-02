@echo off
REM Cloudflare Tunnel Launcher for Market Bot
REM Uses HTTP protocol instead of QUIC for better stability

echo ============================================
echo   Cloudflare Tunnel for Market Bot
echo ============================================
echo.
echo Starting tunnel to localhost:8080...
echo.
echo DO NOT CLOSE THIS WINDOW!
echo Keep this open while using the bot.
echo.
echo Copy the URL when it appears (https://xxxx.trycloudflare.com)
echo.

REM Add cloudflared to PATH
set "PATH=C:\Program Files (x86)\cloudflared;%PATH%"

REM Start tunnel with HTTP protocol (more stable than QUIC)
"C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --protocol http2 --url http://localhost:8080

pause
