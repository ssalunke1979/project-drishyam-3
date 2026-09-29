# Trip Expense Tracker

A Flask-based trip expense management application for 8 members.

## Features

- 8 trip members
- Contribution amount collected by Hitesh
- Trip visit date
- Live clock
- Daily expense tracking
- Breakfast
- Tea
- Coffee
- Lunch
- Dinner
- Fuel
- Toll
- Other expenses
- Exact expense time
- Paid-by member
- Per-expense sharing selection
- Two vehicles
- Vikramsingh Vehicle
- Navendu Vehicle
- Daily expense total
- Total trip expense
- Remaining contribution amount
- Automatic final member split
- Custom final member split
- Settlement suggestions
- GitHub automatic data backup

## Vehicle Accounting

Vehicle expenses can be recorded against:

- Vikramsingh Vehicle
- Navendu Vehicle

For every expense you can select exactly which members share the expense.

## Final Settlement

The application calculates:

Paid by member
minus
Final member share

Positive balance means the member receives money.

Negative balance means the member pays money.

## Custom Split

The automatic split can be manually changed.

The application checks that the custom member shares equal the total trip expense before saving.

## GitHub

The application automatically backs up:

- data/expenses.json
- data/members.json
- data/settings.json

Configure the repository in `.env`.

Example:

GITHUB_REPO_URL=https://github.com/ssalunke1979/project-drishyam-3.git
GITHUB_BRANCH=trip

## Windows

Run:

run_windows.bat

Or:

python app.py

Open:

http://localhost:5000

## Linux

Run:

chmod +x run_linux.sh

./run_linux.sh

Open:

http://localhost:5000