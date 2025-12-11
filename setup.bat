@echo off
echo ============================================
echo LLM Analysis Quiz Solver - Setup Script
echo ============================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

echo [1/4] Creating virtual environment...
python -m venv venv
call venv\Scripts\activate.bat

echo [2/4] Installing Python dependencies...
pip install -r requirements.txt

echo [3/4] Installing Playwright browsers...
playwright install chromium

echo [4/4] Setup complete!
echo.
echo ============================================
echo To start the server, run:
echo   venv\Scripts\activate.bat
echo   python main.py
echo ============================================
echo.
echo Or use: python run_server.py
echo.
pause

