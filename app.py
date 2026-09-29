import json
import os
import subprocess
import uuid
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, flash, jsonify, redirect, render_template, request, url_for


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

EXPENSES_FILE = DATA_DIR / "expenses.json"
MEMBERS_FILE = DATA_DIR / "members.json"
SETTINGS_FILE = DATA_DIR / "settings.json"

load_dotenv(BASE_DIR / ".env")

app = Flask(__name__)
app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    "change-this-secret-key"
)

CATEGORIES = [
    "Breakfast",
    "Tea",
    "Coffee",
    "Lunch",
    "Dinner",
    "Fuel",
    "Toll",
    "Other",
]

VEHICLES = [
    "Vikramsingh Vehicle",
    "Navendu Vehicle",
]

DEFAULT_MEMBERS = [
    "Hitesh",
    "Vikramsingh",
    "Navendu",
    "Member 4",
    "Member 5",
    "Member 6",
    "Member 7",
    "Member 8",
]


# ============================================================
# FILE HELPERS
# ============================================================

def ensure_data_files():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not EXPENSES_FILE.exists():
        save_json(EXPENSES_FILE, [])

    if not MEMBERS_FILE.exists():
        save_json(MEMBERS_FILE, DEFAULT_MEMBERS)

    if not SETTINGS_FILE.exists():
        save_json(
            SETTINGS_FILE,
            {
                "trip_date": datetime.now().strftime("%Y-%m-%d"),
                "contribution_collected": 0,
                "contribution_by": "Hitesh",
            },
        )


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    temp_file = path.with_suffix(path.suffix + ".tmp")

    with open(temp_file, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)

    temp_file.replace(path)


def load_expenses():
    return load_json(EXPENSES_FILE, [])


def load_members():
    members = load_json(MEMBERS_FILE, DEFAULT_MEMBERS)

    if not isinstance(members, list):
        members = DEFAULT_MEMBERS.copy()

    members = members[:8]

    while len(members) < 8:
        members.append(f"Member {len(members) + 1}")

    return members


def load_settings():
    settings = load_json(
        SETTINGS_FILE,
        {
            "trip_date": datetime.now().strftime("%Y-%m-%d"),
            "contribution_collected": 0,
            "contribution_by": "Hitesh",
        },
    )

    if "trip_date" not in settings:
        settings["trip_date"] = datetime.now().strftime("%Y-%m-%d")

    if "contribution_collected" not in settings:
        settings["contribution_collected"] = 0

    if "contribution_by" not in settings:
        settings["contribution_by"] = "Hitesh"

    return settings


# ============================================================
# MONEY HELPERS
# ============================================================

def money(value):
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0.00")


def money_float(value):
    return float(money(value))


def money_string(value):
    return f"{money(value):.2f}"


# ============================================================
# EXPENSE HELPERS
# ============================================================

def get_shared_members(expense, members):
    shared_by = expense.get("shared_by")

    if not shared_by:
        return members.copy()

    valid_members = [
        member for member in shared_by
        if member in members
    ]

    return valid_members or members.copy()


def split_amount(amount, names):
    amount = money(amount)

    if not names:
        return {}

    count = len(names)

    base = (amount / count).quantize(
        Decimal("0.01")
    )

    remainder = amount - (base * count)

    result = {
        name: base
        for name in names
    }

    cents = int(
        (remainder * Decimal("100")).to_integral_value()
    )

    for index in range(abs(cents)):
        name = names[index % count]

        if cents > 0:
            result[name] += Decimal("0.01")
        else:
            result[name] -= Decimal("0.01")

    return result


# ============================================================
# FINANCIAL CALCULATIONS
# ============================================================

def calculate_financials(expenses, members, settings):
    total = Decimal("0.00")

    category_totals = {
        category: Decimal("0.00")
        for category in CATEGORIES
    }

    member_paid = {
        member: Decimal("0.00")
        for member in members
    }

    member_shared = {
        member: Decimal("0.00")
        for member in members
    }

    vehicle_totals = {
        vehicle: Decimal("0.00")
        for vehicle in VEHICLES
    }

    for expense in expenses:
        amount = money(expense.get("amount", 0))

        total += amount

        category = expense.get("category", "Other")

        if category not in category_totals:
            category_totals[category] = Decimal("0.00")

        category_totals[category] += amount

        paid_by = expense.get("paid_by")

        if paid_by in member_paid:
            member_paid[paid_by] += amount

        vehicle = expense.get("vehicle")

        if vehicle in vehicle_totals:
            vehicle_totals[vehicle] += amount

        shared_members = get_shared_members(
            expense,
            members
        )

        shares = split_amount(
            amount,
            shared_members
        )

        for member, share in shares.items():
            if member in member_shared:
                member_shared[member] += share

    custom_final_shares = settings.get(
        "custom_final_shares"
    )

    if custom_final_shares:
        custom_total = sum(
            (
                money(custom_final_shares.get(member, 0))
                for member in members
            ),
            Decimal("0.00"),
        )

        if custom_total == total:
            final_share = {
                member: money(
                    custom_final_shares.get(member, 0)
                )
                for member in members
            }
        else:
            final_share = member_shared.copy()
    else:
        final_share = member_shared.copy()

    balances = {}

    for member in members:
        balances[member] = (
            member_paid[member]
            - final_share[member]
        )

    contribution_collected = money(
        settings.get("contribution_collected", 0)
    )

    remaining = contribution_collected - total

    return {
        "total": total,
        "category_totals": category_totals,
        "member_paid": member_paid,
        "member_shared": member_shared,
        "final_share": final_share,
        "balances": balances,
        "vehicle_totals": vehicle_totals,
        "contribution_collected": contribution_collected,
        "remaining": remaining,
    }


def calculate_settlements(balances):
    creditors = []
    debtors = []

    for member, balance in balances.items():
        balance = money(balance)

        if balance > Decimal("0.00"):
            creditors.append(
                [member, balance]
            )
        elif balance < Decimal("0.00"):
            debtors.append(
                [member, -balance]
            )

    settlements = []

    creditor_index = 0
    debtor_index = 0

    while (
        creditor_index < len(creditors)
        and debtor_index < len(debtors)
    ):
        creditor_name, creditor_amount = creditors[
            creditor_index
        ]

        debtor_name, debtor_amount = debtors[
            debtor_index
        ]

        amount = min(
            creditor_amount,
            debtor_amount
        )

        settlements.append(
            {
                "from": debtor_name,
                "to": creditor_name,
                "amount": amount,
            }
        )

        creditors[creditor_index][1] -= amount
        debtors[debtor_index][1] -= amount

        if creditors[creditor_index][1] <= Decimal("0.00"):
            creditor_index += 1

        if debtors[debtor_index][1] <= Decimal("0.00"):
            debtor_index += 1

    return settlements


# ============================================================
# TIME HELPERS
# ============================================================

def convert_12_hour_to_24(hour, minute, ampm):
    hour = int(hour)
    minute = int(minute)

    ampm = ampm.upper()

    if ampm == "AM":
        if hour == 12:
            hour = 0
    else:
        if hour != 12:
            hour += 12

    return f"{hour:02d}:{minute:02d}"


def format_time_12_hour(time_value):
    if not time_value:
        return ""

    try:
        parsed = datetime.strptime(
            time_value,
            "%H:%M"
        )

        return parsed.strftime("%I:%M %p").lstrip("0")

    except ValueError:
        return time_value


# ============================================================
# GIT AUTO PUSH
# ============================================================

def run_git_command(args):
    result = subprocess.run(
        args,
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip()
            or result.stdout.strip()
            or "Git command failed."
        )

    return result.stdout.strip()


def git_push():
    enabled = os.getenv(
        "GITHUB_AUTO_PUSH",
        "true"
    ).lower() == "true"

    if not enabled:
        return {
            "success": True,
            "message": "Git auto-push disabled."
        }

    repo_url = os.getenv(
        "GITHUB_REPO_URL",
        ""
    ).strip()

    branch = os.getenv(
        "GITHUB_BRANCH",
        "trip"
    ).strip()

    git_name = os.getenv(
        "GIT_USER_NAME",
        "Santosh"
    ).strip()

    git_email = os.getenv(
        "GIT_USER_EMAIL",
        ""
    ).strip()

    if not repo_url:
        return {
            "success": False,
            "message": "GITHUB_REPO_URL is not configured."
        }

    try:
        git_dir = BASE_DIR / ".git"

        if not git_dir.exists():
            run_git_command(["git", "init"])

        try:
            current_origin = run_git_command(
                ["git", "remote", "get-url", "origin"]
            )
        except RuntimeError:
            current_origin = ""

        if current_origin != repo_url:
            if current_origin:
                run_git_command(
                    [
                        "git",
                        "remote",
                        "set-url",
                        "origin",
                        repo_url,
                    ]
                )
            else:
                run_git_command(
                    [
                        "git",
                        "remote",
                        "add",
                        "origin",
                        repo_url,
                    ]
                )

        if git_name:
            run_git_command(
                [
                    "git",
                    "config",
                    "user.name",
                    git_name,
                ]
            )

        if git_email:
            run_git_command(
                [
                    "git",
                    "config",
                    "user.email",
                    git_email,
                ]
            )

        run_git_command(
            [
                "git",
                "add",
                "data/expenses.json",
                "data/members.json",
                "data/settings.json",
            ]
        )

        status = run_git_command(
            [
                "git",
                "status",
                "--porcelain",
            ]
        )

        if not status:
            return {
                "success": True,
                "message": "No data changes to push."
            }

        run_git_command(
            [
                "git",
                "commit",
                "-m",
                "Update trip expense data",
            ]
        )

        run_git_command(
            [
                "git",
                "push",
                "-u",
                "origin",
                branch,
            ]
        )

        return {
            "success": True,
            "message": f"Changes pushed to GitHub branch '{branch}'."
        }

    except Exception as exc:
        return {
            "success": False,
            "message": str(exc),
        }


# ============================================================
# ROUTES
# ============================================================

@app.route("/")
def index():
    ensure_data_files()

    expenses = load_expenses()
    members = load_members()
    settings = load_settings()

    selected_date = request.args.get(
        "date",
        settings.get("trip_date")
    )

    if not selected_date:
        selected_date = datetime.now().strftime(
            "%Y-%m-%d"
        )

    financials = calculate_financials(
        expenses,
        members,
        settings
    )

    daily_expenses = [
        expense
        for expense in expenses
        if expense.get("date") == selected_date
    ]

    daily_total = sum(
        (
            money(expense.get("amount", 0))
            for expense in daily_expenses
        ),
        Decimal("0.00"),
    )

    expenses_sorted = sorted(
        expenses,
        key=lambda item: (
            item.get("date", ""),
            item.get("time", ""),
        ),
        reverse=True,
    )

    for expense in expenses_sorted:
        expense["display_time"] = format_time_12_hour(
            expense.get("time", "")
        )

    settlements = calculate_settlements(
        financials["balances"]
    )

    current_time = datetime.now()

    return render_template(
        "index.html",
        expenses=expenses_sorted,
        daily_expenses=sorted(
            daily_expenses,
            key=lambda item: item.get("time", ""),
            reverse=True,
        ),
        daily_total=daily_total,
        selected_date=selected_date,
        members=members,
        settings=settings,
        categories=CATEGORIES,
        vehicles=VEHICLES,
        financials=financials,
        settlements=settlements,
        current_hour=current_time.strftime("%I").lstrip("0"),
        current_minute=current_time.strftime("%M"),
        current_ampm=current_time.strftime("%p"),
    )


@app.route("/settings", methods=["POST"])
def update_settings():
    settings = load_settings()
    members = load_members()

    trip_date = request.form.get(
        "trip_date",
        ""
    ).strip()

    contribution_collected = request.form.get(
        "contribution_collected",
        "0"
    ).strip()

    contribution_by = request.form.get(
        "contribution_by",
        "Hitesh"
    ).strip()

    try:
        contribution_collected = money(
            contribution_collected
        )
    except Exception:
        contribution_collected = Decimal("0.00")

    if contribution_by not in members:
        contribution_by = "Hitesh"

    settings["trip_date"] = (
        trip_date
        or settings.get("trip_date")
        or datetime.now().strftime("%Y-%m-%d")
    )

    settings["contribution_collected"] = float(
        contribution_collected
    )

    settings["contribution_by"] = contribution_by

    save_json(
        SETTINGS_FILE,
        settings
    )

    result = git_push()

    if result["success"]:
        flash(
            "Settings updated successfully.",
            "success"
        )
    else:
        flash(
            f"Settings saved, but GitHub push failed: "
            f"{result['message']}",
            "warning"
        )

    return redirect(url_for("index"))


@app.route("/members", methods=["POST"])
def update_members():
    old_members = load_members()

    new_members = []

    for index in range(8):
        value = request.form.get(
            f"member_{index}",
            ""
        ).strip()

        new_members.append(
            value or f"Member {index + 1}"
        )

    if len(set(new_members)) != 8:
        flash(
            "All 8 member names must be unique.",
            "error"
        )
        return redirect(url_for("index"))

    expenses = load_expenses()

    for expense in expenses:
        paid_by = expense.get("paid_by")

        if paid_by in old_members:
            old_index = old_members.index(paid_by)
            expense["paid_by"] = new_members[
                old_index
            ]

        shared_by = expense.get("shared_by")

        if shared_by:
            updated_shared = []

            for member in shared_by:
                if member in old_members:
                    old_index = old_members.index(
                        member
                    )

                    new_member = new_members[
                        old_index
                    ]

                    if new_member not in updated_shared:
                        updated_shared.append(
                            new_member
                        )

            expense["shared_by"] = updated_shared

    settings = load_settings()

    if settings.get("contribution_by") in old_members:
        old_index = old_members.index(
            settings["contribution_by"]
        )

        settings["contribution_by"] = new_members[
            old_index
        ]

    custom_split = settings.get(
        "custom_final_shares"
    )

    if custom_split:
        updated_split = {}

        for old_member, amount in custom_split.items():
            if old_member in old_members:
                old_index = old_members.index(
                    old_member
                )

                updated_split[
                    new_members[old_index]
                ] = amount

        settings["custom_final_shares"] = updated_split

    save_json(
        MEMBERS_FILE,
        new_members
    )

    save_json(
        EXPENSES_FILE,
        expenses
    )

    save_json(
        SETTINGS_FILE,
        settings
    )

    result = git_push()

    if result["success"]:
        flash(
            "Members updated successfully.",
            "success"
        )
    else:
        flash(
            f"Members saved, but GitHub push failed: "
            f"{result['message']}",
            "warning"
        )

    return redirect(url_for("index"))


@app.route("/add", methods=["POST"])
def add_expense():
    expenses = load_expenses()
    members = load_members()

    date_value = request.form.get(
        "date",
        ""
    ).strip()

    hour = request.form.get(
        "hour",
        "12"
    ).strip()

    minute = request.form.get(
        "minute",
        "00"
    ).strip()

    ampm = request.form.get(
        "ampm",
        "AM"
    ).strip().upper()

    category = request.form.get(
        "category",
        "Other"
    ).strip()

    amount = request.form.get(
        "amount",
        "0"
    ).strip()

    paid_by = request.form.get(
        "paid_by",
        ""
    ).strip()

    vehicle = request.form.get(
        "vehicle",
        ""
    ).strip()

    location = request.form.get(
        "location",
        ""
    ).strip()

    description = request.form.get(
        "description",
        ""
    ).strip()

    shared_by = request.form.getlist(
        "shared_by"
    )

    if category not in CATEGORIES:
        category = "Other"

    try:
        amount_decimal = money(amount)

        if amount_decimal <= Decimal("0.00"):
            raise ValueError

    except (ValueError, InvalidOperation):
        flash(
            "Please enter a valid expense amount.",
            "error"
        )
        return redirect(url_for("index"))

    if paid_by not in members:
        flash(
            "Please select who paid for the expense.",
            "error"
        )
        return redirect(url_for("index"))

    shared_by = [
        member
        for member in shared_by
        if member in members
    ]

    if not shared_by:
        shared_by = members.copy()

    if category not in ["Fuel", "Toll"]:
        vehicle = ""

    try:
        time_24 = convert_12_hour_to_24(
            hour,
            minute,
            ampm
        )
    except (ValueError, TypeError):
        flash(
            "Please select a valid time.",
            "error"
        )
        return redirect(url_for("index"))

    if not date_value:
        date_value = datetime.now().strftime(
            "%Y-%m-%d"
        )

    expense = {
        "id": str(uuid.uuid4()),
        "date": date_value,
        "time": time_24,
        "category": category,
        "amount": float(amount_decimal),
        "paid_by": paid_by,
        "shared_by": shared_by,
        "vehicle": vehicle,
        "location": location,
        "description": description,
        "created_at": datetime.now().isoformat(
            timespec="seconds"
        ),
    }

    expenses.append(expense)

    settings = load_settings()

    # A changed expense can make an old custom split invalid.
    settings.pop("custom_final_shares", None)

    save_json(
        EXPENSES_FILE,
        expenses
    )

    save_json(
        SETTINGS_FILE,
        settings
    )

    result = git_push()

    if result["success"]:
        flash(
            "Expense added successfully.",
            "success"
        )
    else:
        flash(
            f"Expense saved, but GitHub push failed: "
            f"{result['message']}",
            "warning"
        )

    return redirect(
        url_for(
            "index",
            date=date_value
        )
    )


@app.route("/delete/<expense_id>", methods=["POST"])
def delete_expense(expense_id):
    expenses = load_expenses()

    updated_expenses = [
        expense
        for expense in expenses
        if expense.get("id") != expense_id
    ]

    if len(updated_expenses) == len(expenses):
        flash(
            "Expense not found.",
            "error"
        )
        return redirect(url_for("index"))

    save_json(
        EXPENSES_FILE,
        updated_expenses
    )

    settings = load_settings()
    settings.pop("custom_final_shares", None)

    save_json(
        SETTINGS_FILE,
        settings
    )

    result = git_push()

    if result["success"]:
        flash(
            "Expense deleted successfully.",
            "success"
        )
    else:
        flash(
            f"Expense deleted, but GitHub push failed: "
            f"{result['message']}",
            "warning"
        )

    return redirect(url_for("index"))


@app.route("/custom-split", methods=["POST"])
def custom_split():
    members = load_members()
    expenses = load_expenses()
    settings = load_settings()

    financials = calculate_financials(
        expenses,
        members,
        settings
    )

    total = financials["total"]

    custom_shares = {}
    custom_total = Decimal("0.00")

    for member in members:
        amount = money(
            request.form.get(
                f"share_{member}",
                "0"
            )
        )

        custom_shares[member] = float(amount)
        custom_total += amount

    if custom_total != total:
        flash(
            "Custom final split must exactly equal "
            f"the total trip expense of ₹{total:.2f}.",
            "error"
        )
        return redirect(url_for("index"))

    settings["custom_final_shares"] = custom_shares

    save_json(
        SETTINGS_FILE,
        settings
    )

    result = git_push()

    if result["success"]:
        flash(
            "Custom final split saved.",
            "success"
        )
    else:
        flash(
            f"Custom split saved, but GitHub push failed: "
            f"{result['message']}",
            "warning"
        )

    return redirect(url_for("index"))


@app.route("/clear-custom-split", methods=["POST"])
def clear_custom_split():
    settings = load_settings()

    settings.pop(
        "custom_final_shares",
        None
    )

    save_json(
        SETTINGS_FILE,
        settings
    )

    result = git_push()

    if result["success"]:
        flash(
            "Custom split cleared.",
            "success"
        )
    else:
        flash(
            f"Custom split cleared, but GitHub push failed: "
            f"{result['message']}",
            "warning"
        )

    return redirect(url_for("index"))


@app.route("/api/summary")
def api_summary():
    expenses = load_expenses()
    members = load_members()
    settings = load_settings()

    financials = calculate_financials(
        expenses,
        members,
        settings
    )

    return jsonify(
        {
            "total_expenses": money_float(
                financials["total"]
            ),
            "contribution_collected": money_float(
                financials["contribution_collected"]
            ),
            "remaining": money_float(
                financials["remaining"]
            ),
            "category_totals": {
                category: money_float(amount)
                for category, amount
                in financials["category_totals"].items()
            },
            "vehicle_totals": {
                vehicle: money_float(amount)
                for vehicle, amount
                in financials["vehicle_totals"].items()
            },
            "member_paid": {
                member: money_float(amount)
                for member, amount
                in financials["member_paid"].items()
            },
            "member_shared": {
                member: money_float(amount)
                for member, amount
                in financials["member_shared"].items()
            },
            "final_share": {
                member: money_float(amount)
                for member, amount
                in financials["final_share"].items()
            },
            "balances": {
                member: money_float(amount)
                for member, amount
                in financials["balances"].items()
            },
        }
    )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    ensure_data_files()

    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"

    print("=" * 60)
    print("TRIP EXPENSE TRACKER")
    print("=" * 60)
    print(f"Listening on: {host}:{port}")
    print()
    print("Local:")
    print(f"  http://127.0.0.1:{port}")
    print()
    print("LAN:")
    print(f"  http://192.168.10.x:{port}")
    print("=" * 60)

    app.run(
        host=host,
        port=port,
        debug=debug,
        threaded=True
    )