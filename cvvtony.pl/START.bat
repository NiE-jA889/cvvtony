@echo off
title cvvtony.pl Server
echo ============================================
echo   cvvtony.pl - HUSTLER PACK
echo   Starting server...
echo ============================================
echo.

cd /d "%~dp0"

echo [1/3] Installing dependencies...
call .venv\Scripts\pip.exe install -r requirements.txt --quiet
echo Done.
echo.

echo.

echo [3/3] Starting server at http://localhost:8000
echo.
echo ============================================
echo   Open in browser: http://localhost:8000
echo   To stop: Ctrl+C or close this window
echo ============================================
echo.

timeout /t 2 /nobreak >nul
start http://localhost:8000

.venv\Scripts\python.exe main.py

pause
