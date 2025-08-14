@echo off
REM VespAI Quick Start Script for Windows
echo ========================================
echo VespAI Hornet Detection System
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found! Please install Python 3.7+ first.
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/3] Running automated setup...
python scripts\setup.py
if errorlevel 1 (
    echo ERROR: Setup failed! Check error messages above.
    pause
    exit /b 1
)

echo.
echo [2/3] Setup completed successfully!
echo [3/3] Starting VespAI web interface...
echo.
echo Open your browser to: http://localhost:8081
echo Press Ctrl+C to stop the server
echo.

python main.py --web
pause