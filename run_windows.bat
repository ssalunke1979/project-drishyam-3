@echo off

title Trip Expense Tracker

cd /d "%~dp0"


echo.
echo ========================================
echo       TRIP EXPENSE TRACKER
echo ========================================
echo.


if not exist ".venv\Scripts\python.exe" (

    echo Creating Python virtual environment...

    py -m venv .venv

)


call .venv\Scripts\activate.bat


echo Installing dependencies...

python -m pip install -r requirements.txt


echo.
echo Starting Trip Expense Tracker...
echo.
echo Open:
echo http://localhost:5000
echo.


python app.py


pause

