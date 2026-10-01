@echo off
setlocal

REM ============================================================
REM Trip Expense Tracker - Windows Startup Installer
REM ============================================================

REM Change this to your actual project folder
set "APP_DIR=C:\TripExpenseTracker"

REM BAT file that starts the application
set "APP_BAT=%APP_DIR%\start_app.bat"

REM Windows Startup folder
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"

REM Shortcut name
set "SHORTCUT_NAME=Trip Expense Tracker.lnk"

echo.
echo ============================================
echo   Trip Expense Tracker Startup Setup
echo ============================================
echo.

REM Check application BAT file
if not exist "%APP_BAT%" (
    echo ERROR: Application startup file not found:
    echo %APP_BAT%
    echo.
    pause
    exit /b 1
)

echo Creating Startup shortcut...

powershell -NoProfile -ExecutionPolicy Bypass -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%STARTUP_DIR%\%SHORTCUT_NAME%'); $Shortcut.TargetPath = '%APP_BAT%'; $Shortcut.WorkingDirectory = '%APP_DIR%'; $Shortcut.WindowStyle = 7; $Shortcut.Save()"

if exist "%STARTUP_DIR%\%SHORTCUT_NAME%" (
    echo.
    echo SUCCESS!
    echo.
    echo Trip Expense Tracker will start automatically
    echo when you log into Windows.
    echo.
) else (
    echo.
    echo ERROR: Failed to create Startup shortcut.
    echo.
)

pause