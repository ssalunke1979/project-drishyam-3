@echo off

set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT_NAME=Trip Expense Tracker.lnk"

if exist "%STARTUP_DIR%\%SHORTCUT_NAME%" (
    del "%STARTUP_DIR%\%SHORTCUT_NAME%"
    echo Startup entry removed successfully.
) else (
    echo Startup entry was not found.
)

pause