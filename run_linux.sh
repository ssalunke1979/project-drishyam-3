#!/usr/bin/env bash

set -e


cd "$(dirname "$0")"


echo
echo "========================================"
echo "       TRIP EXPENSE TRACKER"
echo "========================================"
echo


if [ ! -x ".venv/bin/python" ]; then

    echo "Creating Python virtual environment..."

    python3 -m venv .venv

fi


source .venv/bin/activate


echo "Installing dependencies..."

python -m pip install -r requirements.txt


echo
echo "Starting Trip Expense Tracker..."
echo
echo "Open:"
echo "http://localhost:5000"
echo


python app.py

