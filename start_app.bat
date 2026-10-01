@echo off
setlocal

cd /d "%~dp0"

if not exist "app.py" (
    echo ERROR: app.py not found.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Python virtual environment not found.
    echo Expected: %~dp0.venv\Scripts\python.exe
    pause
    exit /b 1
)

".venv\Scripts\python.exe" app.py

pause