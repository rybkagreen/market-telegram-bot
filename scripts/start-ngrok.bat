@echo off
REM Ngrok Tunnel for Market Bot

echo ============================================
echo   Ngrok Tunnel for Market Bot
echo ============================================
echo.
echo Starting ngrok to localhost:8080...
echo.
echo DO NOT CLOSE THIS WINDOW!
echo.
echo Your URL will be displayed here.
echo Copy it and update .env file.
echo.

ngrok http 8080 --log=stdout

pause
