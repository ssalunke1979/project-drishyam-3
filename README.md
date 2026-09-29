# Trip Expense Tracker

A Python Flask application for tracking expenses for an 8-member trip.


## Expense Categories

The application supports:

- Petrol
- Lunch
- Dinner
- Drinks
- Toll
- Other


## Each Expense Contains

Every expense stores:

- Date
- Time
- Category
- Amount
- Person who paid
- Location
- Description
- Receipt / bill reference
- Creation timestamp


## Dashboard

The dashboard displays:

- Total trip expense
- Number of expense entries
- Equal share per member
- Category-wise totals
- Category chart
- Amount paid by each member
- Member settlement difference
- Complete expense history


# Installation - Windows


## 1. Install Python

Install Python 3.10 or newer.


## 2. Install Git

Install Git for Windows.


## 3. Create virtual environment

Open PowerShell inside the project directory:

```powershell
py -m venv .venv
````

## 4. Activate environment

```powershell
.\.venv\Scripts\Activate.ps1
```

## 5. Install packages

```powershell
pip install -r requirements.txt
```

## 6. Start application

```powershell
python app.py
```

Open:

```text
http://localhost:5000
```

# GitHub Setup

Create a private GitHub repository.

Example:

```text
trip-expense-tracker
```

Then configure Git:

```powershell
git config --global user.name "YOUR NAME"

git config --global user.email "YOUR EMAIL"
```

Initialize the repository:

```powershell
git init

git branch -M main
```

Add your GitHub remote:

```powershell
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
```

Initial push:

```powershell
git add .

git commit -m "Initial trip expense tracker"

git push -u origin main
```

## GitHub Authentication

Do not put your GitHub password or token inside `app.py`.

Use Git Credential Manager or SSH authentication.

Once:

```text
git push
```

works successfully from PowerShell, the application can automatically execute:

```text
git add
git commit
git push
```

whenever expense data changes.

# Linux / Ubuntu

Create environment:

```bash
python3 -m venv .venv
```

Activate:

```bash
source .venv/bin/activate
```

Install:

```bash
pip install -r requirements.txt
```

Run:

```bash
python app.py
```

Open:

```text
http://localhost:5000
```

# LAN Access

The Flask server listens on:

```text
0.0.0.0
```

Therefore another device on the same network can access it.

Find your computer IP:

Windows:

```powershell
ipconfig
```

Example:

```text
192.168.1.20
```

Then use:

```text
http://192.168.1.20:5000
```

# Data

Trip expense data:

```text
data/expenses.json
```

Member names:

```text
data/members.json
```

# GitHub Backup

When an expense is added:

```text
data/expenses.json
        ↓
git add
        ↓
git commit
        ↓
git push
        ↓
GitHub
```

When an expense is deleted, the same process occurs.

# Security

Use a private GitHub repository.

Do not commit:

```text
.env
```

Do not put:

```text
GitHub password
GitHub token
SSH private key
```

inside the application source code.

# Future Enhancements

Possible next versions can add:

* Receipt photo upload
* Camera capture
* Individual expense splitting
* Automatic settlement calculation
* Cash / UPI / Card
* Petrol quantity in litres
* Petrol price per litre
* Vehicle number
* KM travelled
* Toll plaza name
* Lunch restaurant
* Dinner restaurant
* Drinks details
* Excel export
* PDF report
* WhatsApp sharing
* Multiple trips
* Login
* Mobile PWA
* GitHub sync status
* Automatic daily backup


