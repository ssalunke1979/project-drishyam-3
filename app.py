import json
import os
import subprocess
import uuid
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from dotenv import load_dotenv
from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

EXPENSES_FILE = DATA_DIR / "expenses.json"
MEMBERS_FILE = DATA_DIR / "members.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(BASE_DIR / ".env")


app = Flask(__name__)

app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    "trip-expense-local-secret"
)


CATEGORIES = [
    "Petrol",
    "Lunch",
    "Dinner",
    "Drinks",
    "Toll",
    "Other",
]


DEFAULT_MEMBERS = [
    "Member 1",
    "Member 2",
    "Member 3",
    "Member 4",
    "Member 5",
    "Member 6",
    "Member 7",
    "Member 8",
]


# ============================================================
# JSON HELPERS
# ============================================================

def load_json(path, default):
    try:
        if not path.exists():
            save_json(path, default)
            return default

        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)

    except (json.JSONDecodeError, OSError):
        return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False,
        )


def load_expenses():
    data = load_json(EXPENSES_FILE, [])

    if not isinstance(data, list):
        return []

    return data


def load_members():
    data = load_json(
        MEMBERS_FILE,
        DEFAULT_MEMBERS,
    )

    if not isinstance(data, list):
        return DEFAULT_MEMBERS.copy()

    members = [
        str(member).strip()
        for member in data
        if str(member).strip()
    ]

    while len(members) < 8:
        members.append(
            f"Member {len(members) + 1}"
        )

    return members[:8]


# ============================================================
# MONEY HELPERS
# ============================================================

def decimal_money(value):
    return Decimal(
        str(value)
    ).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


def money_float(value):
    return float(
        decimal_money(value)
    )


# ============================================================
# EXPENSE MEMBER SPLITTING
# ============================================================

def get_shared_members(expense, members):
    """
    Returns the members who participated in this expense.

    Older expense records without shared_by are treated as
    shared by all members for backward compatibility.
    """

    shared_by = expense.get("shared_by")

    if not isinstance(shared_by, list):
        return members.copy()

    valid_members = [
        member
        for member in shared_by
        if member in members
    ]

    if not valid_members:
        return members.copy()

    return valid_members


def split_amount(amount, shared_members):
    """
    Splits an amount exactly in paisa/cents.

    Example:
        ₹100 / 3

    becomes:
        ₹33.34
        ₹33.33
        ₹33.33

    This ensures the total remains exactly ₹100.
    """

    if not shared_members:
        return {}

    amount = decimal_money(amount)

    total_paisa = int(
        amount * 100
    )

    base_paisa, remainder = divmod(
        total_paisa,
        len(shared_members),
    )

    result = {}

    for index, member in enumerate(shared_members):

        paisa = base_paisa

        if index < remainder:
            paisa += 1

        result[member] = (
            Decimal(paisa) / Decimal(100)
        )

    return result


# ============================================================
# FINANCIAL CALCULATIONS
# ============================================================

def calculate_financials(expenses, members):

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


    for expense in expenses:

        try:
            amount = decimal_money(
                expense.get("amount", 0)
            )
        except Exception:
            continue


        total += amount


        category = expense.get(
            "category",
            "Other",
        )

        if category not in category_totals:
            category_totals[category] = (
                Decimal("0.00")
            )

        category_totals[category] += amount


        # ----------------------------------------------------
        # WHO PAID
        # ----------------------------------------------------

        paid_by = expense.get("paid_by")

        if paid_by in member_paid:
            member_paid[paid_by] += amount


        # ----------------------------------------------------
        # WHO SHARED / CONSUMED
        # ----------------------------------------------------

        shared_members = get_shared_members(
            expense,
            members,
        )

        shares = split_amount(
            amount,
            shared_members,
        )

        for member, share in shares.items():

            if member in member_shared:
                member_shared[member] += share


    # --------------------------------------------------------
    # BALANCE
    #
    # Positive = member should receive money
    # Negative = member should pay money
    # --------------------------------------------------------

    balances = {}

    for member in members:

        balances[member] = (
            member_paid[member]
            - member_shared[member]
        )


    # --------------------------------------------------------
    # SETTLEMENT
    # --------------------------------------------------------

    settlements = calculate_settlements(
        balances
    )


    return {
        "total": total,
        "category_totals": category_totals,
        "member_paid": member_paid,
        "member_shared": member_shared,
        "balances": balances,
        "settlements": settlements,
    }


# ============================================================
# SETTLEMENT CALCULATION
# ============================================================

def calculate_settlements(balances):

    creditors = []
    debtors = []


    for member, balance in balances.items():

        balance = decimal_money(balance)

        if balance > Decimal("0.00"):

            creditors.append(
                {
                    "member": member,
                    "amount": balance,
                }
            )

        elif balance < Decimal("0.00"):

            debtors.append(
                {
                    "member": member,
                    "amount": -balance,
                }
            )


    # Largest amounts first.
    creditors.sort(
        key=lambda item: item["amount"],
        reverse=True,
    )

    debtors.sort(
        key=lambda item: item["amount"],
        reverse=True,
    )


    settlements = []


    creditor_index = 0
    debtor_index = 0


    while (
        creditor_index < len(creditors)
        and debtor_index < len(debtors)
    ):

        creditor = creditors[
            creditor_index
        ]

        debtor = debtors[
            debtor_index
        ]


        transfer = min(
            creditor["amount"],
            debtor["amount"],
        )

        transfer = decimal_money(
            transfer
        )


        if transfer > Decimal("0.00"):

            settlements.append(
                {
                    "from": debtor["member"],
                    "to": creditor["member"],
                    "amount": transfer,
                }
            )


        creditor["amount"] -= transfer
        debtor["amount"] -= transfer


        if creditor["amount"] <= Decimal("0.00"):
            creditor_index += 1


        if debtor["amount"] <= Decimal("0.00"):
            debtor_index += 1


    return settlements


# ============================================================
# GITHUB
# ============================================================

def git_push(message):

    auto_push = os.getenv(
        "GITHUB_AUTO_PUSH",
        "true",
    ).lower() in (
        "true",
        "1",
        "yes",
        "on",
    )

    if not auto_push:
        return True, "GitHub auto-push disabled."


    try:

        subprocess.run(
            [
                "git",
                "add",
                "data/expenses.json",
                "data/members.json",
            ],
            cwd=BASE_DIR,
            check=True,
            capture_output=True,
            text=True,
        )


        status = subprocess.run(
            [
                "git",
                "status",
                "--porcelain",
            ],
            cwd=BASE_DIR,
            check=True,
            capture_output=True,
            text=True,
        )


        if not status.stdout.strip():

            return True, "No Git changes required."


        subprocess.run(
            [
                "git",
                "commit",
                "-m",
                message,
            ],
            cwd=BASE_DIR,
            check=True,
            capture_output=True,
            text=True,
        )


        subprocess.run(
            [
                "git",
                "push",
            ],
            cwd=BASE_DIR,
            check=True,
            capture_output=True,
            text=True,
        )


        return True, "Changes pushed to GitHub."


    except subprocess.CalledProcessError as exc:

        error = (
            exc.stderr
            or exc.stdout
            or str(exc)
        )

        return (
            False,
            f"GitHub push failed: {error}",
        )

    except FileNotFoundError:

        return (
            False,
            "Git is not installed or not available in PATH.",
        )


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/")
def dashboard():

    members = load_members()

    expenses = load_expenses()


    financials = calculate_financials(
        expenses,
        members,
    )


    # --------------------------------------------------------
    # Prepare expenses for UI
    # --------------------------------------------------------

    display_expenses = []

    for expense in expenses:

        item = dict(expense)

        shared_members = get_shared_members(
            expense,
            members,
        )

        item["shared_by_display"] = (
            shared_members
        )

        item["shared_count"] = len(
            shared_members
        )

        shares = split_amount(
            expense.get("amount", 0),
            shared_members,
        )

        item["shares_display"] = [
            {
                "member": member,
                "amount": money_float(amount),
            }
            for member, amount in shares.items()
        ]

        display_expenses.append(item)


    # Newest first

    display_expenses.sort(
        key=lambda item: (
            item.get("date", ""),
            item.get("time", ""),
        ),
        reverse=True,
    )


    now = datetime.now()


    member_rows = []

    for member in members:

        member_rows.append(
            {
                "name": member,
                "paid": money_float(
                    financials["member_paid"][
                        member
                    ]
                ),
                "shared": money_float(
                    financials["member_shared"][
                        member
                    ]
                ),
                "balance": money_float(
                    financials["balances"][
                        member
                    ]
                ),
            }
        )


    settlement_rows = [
        {
            "from": item["from"],
            "to": item["to"],
            "amount": money_float(
                item["amount"]
            ),
        }
        for item in financials["settlements"]
    ]


    return render_template(
        "index.html",

        members=members,

        expenses=display_expenses,

        categories=CATEGORIES,

        total=money_float(
            financials["total"]
        ),

        category_totals={
            category: money_float(amount)
            for category, amount
            in financials[
                "category_totals"
            ].items()
        },

        member_paid={
            member: money_float(amount)
            for member, amount
            in financials[
                "member_paid"
            ].items()
        },

        member_shared={
            member: money_float(amount)
            for member, amount
            in financials[
                "member_shared"
            ].items()
        },

        balances={
            member: money_float(amount)
            for member, amount
            in financials[
                "balances"
            ].items()
        },

        member_rows=member_rows,

        settlements=settlement_rows,

        now_date=now.strftime(
            "%Y-%m-%d"
        ),

        now_time=now.strftime(
            "%H:%M"
        ),
    )


# ============================================================
# ADD EXPENSE
# ============================================================

@app.route(
    "/add",
    methods=["POST"],
)
def add_expense():

    members = load_members()


    category = (
        request.form.get(
            "category",
            "Other",
        ).strip()
    )


    if category not in CATEGORIES:
        category = "Other"


    paid_by = (
        request.form.get(
            "paid_by",
            "",
        ).strip()
    )


    if paid_by not in members:

        flash(
            "Please select a valid member who paid the expense.",
            "error",
        )

        return redirect(
            url_for("dashboard")
        )


    # --------------------------------------------------------
    # Shared members
    # --------------------------------------------------------

    shared_by = request.form.getlist(
        "shared_by"
    )


    shared_by = [
        member
        for member in shared_by
        if member in members
    ]


    if not shared_by:

        flash(
            "Select at least one member who shared this expense.",
            "error",
        )

        return redirect(
            url_for("dashboard")
        )


    # --------------------------------------------------------
    # Amount
    # --------------------------------------------------------

    try:

        amount = decimal_money(
            request.form.get(
                "amount",
                "0",
            )
        )

        if amount <= Decimal("0.00"):

            raise ValueError

    except Exception:

        flash(
            "Please enter a valid expense amount.",
            "error",
        )

        return redirect(
            url_for("dashboard")
        )


    # --------------------------------------------------------
    # Create expense
    # --------------------------------------------------------

    expense = {

        "id": uuid.uuid4().hex,

        "date": request.form.get(
            "date",
            datetime.now().strftime(
                "%Y-%m-%d"
            ),
        ),

        "time": request.form.get(
            "time",
            datetime.now().strftime(
                "%H:%M"
            ),
        ),

        "category": category,

        "amount": money_float(
            amount
        ),

        "paid_by": paid_by,

        "shared_by": shared_by,

        "location": request.form.get(
            "location",
            "",
        ).strip(),

        "description": request.form.get(
            "description",
            "",
        ).strip(),

        "receipt": request.form.get(
            "receipt",
            "",
        ).strip(),

        "created_at":
            datetime.now().isoformat(
                timespec="seconds"
            ),
    }


    expenses = load_expenses()

    expenses.append(expense)

    save_json(
        EXPENSES_FILE,
        expenses,
    )


    success, message = git_push(
        f"Add {category} expense - ₹{amount}"
    )


    if success:

        flash(
            "Expense added successfully. "
            + message,
            "success",
        )

    else:

        flash(
            "Expense saved locally. "
            + message,
            "error",
        )


    return redirect(
        url_for("dashboard")
    )


# ============================================================
# DELETE EXPENSE
# ============================================================

@app.route(
    "/delete/<expense_id>",
    methods=["POST"],
)
def delete_expense(expense_id):

    expenses = load_expenses()


    original_count = len(expenses)


    expenses = [
        expense
        for expense in expenses
        if expense.get("id") != expense_id
    ]


    if len(expenses) == original_count:

        flash(
            "Expense not found.",
            "error",
        )

        return redirect(
            url_for("dashboard")
        )


    save_json(
        EXPENSES_FILE,
        expenses,
    )


    success, message = git_push(
        "Delete trip expense"
    )


    if success:

        flash(
            "Expense deleted. "
            + message,
            "success",
        )

    else:

        flash(
            "Expense deleted locally. "
            + message,
            "error",
        )


    return redirect(
        url_for("dashboard")
    )


# ============================================================
# UPDATE MEMBERS
# ============================================================

@app.route(
    "/members",
    methods=["POST"],
)
def update_members():

    old_members = load_members()


    new_members = []


    for index in range(1, 9):

        name = request.form.get(
            f"member{index}",
            "",
        ).strip()

        if not name:

            name = f"Member {index}"

        new_members.append(name)


    # --------------------------------------------------------
    # Unique names
    # --------------------------------------------------------

    if len(set(new_members)) != 8:

        flash(
            "Each member must have a unique name.",
            "error",
        )

        return redirect(
            url_for("dashboard")
        )


    # --------------------------------------------------------
    # Preserve existing expenses when member names change
    #
    # Example:
    # Member 1 -> Santosh
    #
    # Existing expenses for Member 1 are automatically changed
    # to Santosh.
    # --------------------------------------------------------

    expenses = load_expenses()


    rename_map = {}

    for index in range(8):

        old_name = old_members[index]

        new_name = new_members[index]

        rename_map[old_name] = new_name


    for expense in expenses:

        old_paid_by = expense.get(
            "paid_by"
        )

        if old_paid_by in rename_map:

            expense["paid_by"] = (
                rename_map[old_paid_by]
            )


        old_shared_by = expense.get(
            "shared_by"
        )


        if isinstance(
            old_shared_by,
            list,
        ):

            expense["shared_by"] = [

                rename_map.get(
                    member,
                    member,
                )

                for member in old_shared_by

            ]


    save_json(
        MEMBERS_FILE,
        new_members,
    )


    save_json(
        EXPENSES_FILE,
        expenses,
    )


    success, message = git_push(
        "Update trip members"
    )


    if success:

        flash(
            "Members updated. "
            + message,
            "success",
        )

    else:

        flash(
            "Members updated locally. "
            + message,
            "error",
        )


    return redirect(
        url_for("dashboard")
    )


# ============================================================
# API
# ============================================================

@app.route("/api/summary")
def api_summary():

    members = load_members()

    expenses = load_expenses()


    financials = calculate_financials(
        expenses,
        members,
    )


    return jsonify(

        {

            "total":
                money_float(
                    financials["total"]
                ),

            "categories": {

                category:
                    money_float(amount)

                for category, amount
                in financials[
                    "category_totals"
                ].items()

            },

            "members": {

                member: {

                    "paid":
                        money_float(
                            financials[
                                "member_paid"
                            ][member]
                        ),

                    "shared":
                        money_float(
                            financials[
                                "member_shared"
                            ][member]
                        ),

                    "balance":
                        money_float(
                            financials[
                                "balances"
                            ][member]
                        ),

                }

                for member in members

            },

            "settlements": [

                {

                    "from":
                        item["from"],

                    "to":
                        item["to"],

                    "amount":
                        money_float(
                            item["amount"]
                        ),

                }

                for item
                in financials[
                    "settlements"
                ]

            ],

        }

    )


# ============================================================
# START APPLICATION
# ============================================================

if __name__ == "__main__":

    host = os.getenv(
        "FLASK_HOST",
        "0.0.0.0",
    )

    port = int(
        os.getenv(
            "FLASK_PORT",
            "5000",
        )
    )

    debug = (
        os.getenv(
            "FLASK_DEBUG",
            "false",
        ).lower()
        in ("true", "1", "yes")
    )


    print()
    print("=" * 60)
    print(" Trip Expense Tracker")
    print("=" * 60)
    print()
    print(
        f" Open: http://localhost:{port}"
    )
    print()
    print(
        " Per-expense member splitting: ENABLED"
    )
    print(
        " GitHub auto-push: "
        + os.getenv(
            "GITHUB_AUTO_PUSH",
            "true",
        )
    )
    print()
    print("=" * 60)
    print()


    app.run(
        host=host,
        port=port,
        debug=debug,
    )