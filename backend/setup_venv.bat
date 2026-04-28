@echo off
REM Windows virtual environment setup script

echo ==========================================
echo Setting up virtual environment...
echo ==========================================

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed!
    exit /b 1
)

REM Create virtual environment
echo Creating virtual environment...
python -m venv venv

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

echo ==========================================
echo Virtual environment setup complete!
echo ==========================================
echo.
echo To activate the virtual environment:
echo   venv\Scripts\activate
echo.
echo To run the server:
echo   python main.py
echo.
pause
