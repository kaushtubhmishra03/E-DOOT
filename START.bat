@echo off
TITLE E-Doot: Emergency-First Healthcare Platform
COLOR 0B

echo ========================================================
echo         E-DOOT : EMERGENCY HEALTHCARE NETWORK
echo ========================================================
echo.
echo [1/4] Checking Python environment...
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    COLOR 0C
    echo [ERROR] Python is not found in PATH!
    echo Please install Python 3.10+ from python.org and add it to PATH.
    pause
    exit /b 1
)

echo [2/4] Ensuring project dependencies are installed...
python -m pip install -r requirements.txt --quiet

echo [3/4] Checking database and mock seed records...
IF NOT EXIST "edoot.db" (
    echo Database not found. Initializing and seeding 8 hospitals and 3 patients...
    python seed.py
)

echo [4/4] Launching E-Doot Local Server...
echo.
echo ========================================================
echo   Server URL: http://127.0.0.1:5000
echo   Patient App: http://127.0.0.1:5000/app
echo   Emergency QR: http://127.0.0.1:5000/app/emergency/rahul-qr-demo-token-101
echo   Doctor/Admin: http://127.0.0.1:5000/portal
echo ========================================================
echo.
echo Opening default web browser in 2 seconds...
timeout /t 2 /nobreak >nul
start http://127.0.0.1:5000

echo Starting Flask Application (Press Ctrl+C to stop)...
python app.py
IF ERRORLEVEL 1 (
    echo.
    echo Application stopped with an exit code.
    pause
)
