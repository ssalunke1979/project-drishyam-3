@echo off

setlocal

cd /d "%~dp0"


echo.
echo ============================================
echo          MOVIE VLC LIBRARY
echo ============================================
echo


set "PY=python"

where python >nul 2>&1

if errorlevel 1 (

    where py >nul 2>&1

    if errorlevel 1 (

        echo [ERROR] Python 3 is not installed
        echo or not available in PATH.

        pause

        exit /b 1
    )

    set "PY=py -3"
)


if not exist ".venv\Scripts\python.exe" (

    echo Creating virtual environment...

    %PY% -m venv .venv

)


echo Installing dependencies (Flask + player: PyQt5, PyAV, sounddevice)...

.venv\Scripts\python.exe ^
    -m pip install --upgrade pip

.venv\Scripts\python.exe ^
    -m pip install -r requirements.txt


if not exist "videos\Movies" (
    mkdir "videos\Movies"
)

if not exist "videos\Series" (
    mkdir "videos\Series"
)


echo.
echo Browser will open in a few seconds...

rem Open the browser AFTER the server has had time to start.
start "" /min cmd /c "timeout /t 3 /nobreak >nul & start http://127.0.0.1:5000"


echo.
echo Starting server...
echo Press CTRL+C to stop.
echo.


.venv\Scripts\python.exe app.py


pause
