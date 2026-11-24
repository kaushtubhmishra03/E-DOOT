@echo off
TITLE Reset E-Doot Demo Database
COLOR 0E

echo ========================================================
echo     RESETTING E-DOOT MOCK DATABASE TO DEMO STATE
echo ========================================================
echo.
echo Re-seeding 8 Delhi/NCR hospitals, doctors, and 3 mock patients...
python seed.py
IF ERRORLEVEL 1 (
    COLOR 0C
    echo [ERROR] Failed to reset database.
    pause
    exit /b 1
)

COLOR 0A
echo.
echo [SUCCESS] Database reset complete!
echo Ready for fresh hackathon demonstration.
echo.
pause
