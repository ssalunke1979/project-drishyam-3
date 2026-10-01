import json
import os
import uuid
from datetime import datetime, date
from functools import wraps

from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import (
    check_password_hash,
    generate_password_hash,
)

from config import (
    HOST,
    PORT,
    DEBUG,
    APP_HOSTNAME,
    PUBLIC_URL,
    SECRET_KEY,
    DASHBOARD_USERNAME,
    DASHBOARD_PASSWORD,
    SESSION_COOKIE_SECURE,
    SESSION_COOKIE_HTTPONLY,
    SESSION_COOKIE_SAMESITE,
)


# =========================================================
# APPLICATION
# =========================================================

app = Flask(__name__)

app.secret_key = SECRET_KEY

app.config["SESSION_COOKIE_SECURE"] = SESSION_COOKIE_SECURE
app.config["SESSION_COOKIE_HTTPONLY"] = SESSION_COOKIE_HTTPONLY
app.config["SESSION_COOKIE_SAMESITE"] = SESSION_COOKIE_SAMESITE

app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_for=1,
    x_proto=1,
    x_host=1,
)


# =========================================================
# DIRECTORIES
# =========================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DATA_DIR = os.path.join(
    BASE_DIR,
    "data"
)

MEMBERS_FILE = os.path.join(
    DATA_DIR,
    "members.json"
)

SETTINGS_FILE = os.path.join(
    DATA_DIR,
    "settings.json"
)

EXPENSES_FILE = os.path.join(
    DATA_DIR,
    "expenses.json"
)

USERS_FILE = os.path.join(
    DATA_DIR,
    "users.json"
)


# =========================================================
# DEFAULT DATA
# =========================================================

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


CATEGORIES = [
    "Drinks",
    "Food",
    "Fuel",
    "Toll",
    "Hotel",
    "Travel",
    "Tickets",
    "Parking",
    "Shopping",
    "Other",
]


VEHICLES = [
    "Vikramsingh",
    "Navendu",
]


DEFAULT_SETTINGS = {
    "trip_date": date.today().isoformat(),
    "contribution_collected": 0.0,
    "contribution_by": "Hitesh",
    "member_contributions": {},
    "custom_final_shares": {},
}


# =========================================================
# JSON HELPERS
# =========================================================

def save_json(path, data):
    os.makedirs(
        os.path.dirname(path),
        exist_ok=True,
    )

    temporary_file = path + ".tmp"

    with open(
        temporary_file,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False,
        )

    os.replace(
        temporary_file,
        path,
    )


def load_json(path, default):
    try:
        with open(
            path,
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)

    except (
        FileNotFoundError,
        json.JSONDecodeError,
        OSError,
    ):
        return default


# =========================================================
# INITIAL DATA
# =========================================================

def ensure_data_files():

    os.makedirs(
        DATA_DIR,
        exist_ok=True,
    )

    if not os.path.exists(MEMBERS_FILE):
        save_json(
            MEMBERS_FILE,
            DEFAULT_MEMBERS,
        )

    if not os.path.exists(SETTINGS_FILE):
        save_json(
            SETTINGS_FILE,
            DEFAULT_SETTINGS,
        )

    if not os.path.exists(EXPENSES_FILE):
        save_json(
            EXPENSES_FILE,
            [],
        )

    if not os.path.exists(USERS_FILE):
        save_json(
            USERS_FILE,
            [],
        )

    synchronize_users()


def load_members():
    members = load_json(
        MEMBERS_FILE,
        DEFAULT_MEMBERS,
    )

    if not isinstance(members, list):
        return DEFAULT_MEMBERS.copy()

    return members


def load_settings():
    settings = load_json(
        SETTINGS_FILE,
        DEFAULT_SETTINGS.copy(),
    )

    if not isinstance(settings, dict):
        settings = DEFAULT_SETTINGS.copy()

    return settings


def load_expenses():
    expenses = load_json(
        EXPENSES_FILE,
        [],
    )

    if not isinstance(expenses, list):
        return []

    return expenses


def load_users():
    users = load_json(
        USERS_FILE,
        [],
    )

    if not isinstance(users, list):
        return []

    return users


# =========================================================
# USER MANAGEMENT
# =========================================================

def synchronize_users():

    members = load_members()
    users = load_users()

    existing_members = {
        user.get("member")
        for user in users
        if isinstance(user, dict)
    }

    changed = False

    for member in members:

        if member in existing_members:
            continue

        username = make_unique_username(
            member,
            users,
        )

        users.append(
            {
                "username": username,
                "password_hash": generate_password_hash(
                    "change-me"
                ),
                "member": member,
                "access": "read",
                "enabled": True,
                "must_change_password": True,
            }
        )

        changed = True

    valid_members = set(members)

    filtered_users = [
        user
        for user in users
        if user.get("member") in valid_members
    ]

    if len(filtered_users) != len(users):
        users = filtered_users
        changed = True

    if changed:
        save_json(
            USERS_FILE,
            users,
        )


def make_unique_username(member, users):

    base = "".join(
        character.lower()
        if character.isalnum()
        else "_"
        for character in member
    ).strip("_")

    if not base:
        base = "member"

    username = base
    counter = 2

    existing = {
        user.get("username", "").lower()
        for user in users
    }

    while username.lower() in existing:
        username = f"{base}{counter}"
        counter += 1

    return username


# =========================================================
# AUTHENTICATION
# =========================================================

def get_current_user():

    if not session.get("logged_in"):
        return None

    return {
        "username": session.get("username"),
        "member": session.get("member"),
        "access": session.get("access"),
        "is_admin": session.get("is_admin", False),
    }


def login_user(
    username,
    member=None,
    access="read",
    is_admin=False,
):

    session.clear()

    session["logged_in"] = True
    session["username"] = username
    session["member"] = member
    session["access"] = access
    session["is_admin"] = is_admin


def logout_user():

    session.clear()


def is_admin():

    return (
        session.get("logged_in")
        and session.get("is_admin") is True
    )


def has_write_access():

    if not session.get("logged_in"):
        return False

    if session.get("is_admin") is True:
        return True

    return session.get("access") == "write"


def login_required(view):

    @wraps(view)
    def wrapped(*args, **kwargs):

        if not session.get("logged_in"):
            flash(
                "Please login first.",
                "error",
            )

            return redirect(
                url_for("login")
            )

        return view(*args, **kwargs)

    return wrapped


def write_required(view):

    @wraps(view)
    def wrapped(*args, **kwargs):

        if not session.get("logged_in"):
            return redirect(
                url_for("login")
            )

        if not has_write_access():

            flash(
                "Read-only access. You cannot modify trip data.",
                "error",
            )

            return redirect(
                url_for("index")
            )

        return view(*args, **kwargs)

    return wrapped


def admin_required(view):

    @wraps(view)
    def wrapped(*args, **kwargs):

        if not session.get("logged_in"):
            return redirect(
                url_for("login")
            )

        if not is_admin():

            flash(
                "Administrator access required.",
                "error",
            )

            return redirect(
                url_for("index")
            )

        return view(*args, **kwargs)

    return wrapped


# =========================================================
# LOGIN
# =========================================================

@app.route(
    "/login",
    methods=["GET", "POST"],
)
def login():

    if session.get("logged_in"):
        if is_admin():
            return redirect(
                url_for("dashboard")
            )

        return redirect(
            url_for("index")
        )

    if request.method == "POST":

        username = request.form.get(
            "username",
            "",
        ).strip()

        password = request.form.get(
            "password",
            "",
        )

        if (
            username == DASHBOARD_USERNAME
            and password == DASHBOARD_PASSWORD
        ):

            login_user(
                username=username,
                is_admin=True,
                access="write",
            )

            return redirect(
                url_for("dashboard")
            )

        users = load_users()

        matched_user = None

        for user in users:

            if (
                user.get("username", "").lower()
                == username.lower()
            ):
                matched_user = user
                break

        if matched_user is None:

            flash(
                "Invalid username or password.",
                "error",
            )

            return render_template(
                "login.html"
            )

        if not matched_user.get(
            "enabled",
            True,
        ):

            flash(
                "This account is disabled.",
                "error",
            )

            return render_template(
                "login.html"
            )

        password_hash = matched_user.get(
            "password_hash",
            "",
        )

        if not check_password_hash(
            password_hash,
            password,
        ):

            flash(
                "Invalid username or password.",
                "error",
            )

            return render_template(
                "login.html"
            )

        login_user(
            username=matched_user["username"],
            member=matched_user["member"],
            access=matched_user.get(
                "access",
                "read",
            ),
            is_admin=False,
        )

        if matched_user.get(
            "must_change_password",
            False,
        ):

            flash(
                "Please ask the administrator to change your initial password.",
                "info",
            )

        return redirect(
            url_for("index")
        )

    return render_template(
        "login.html"
    )


@app.route("/logout")
def logout():

    logout_user()

    return redirect(
        url_for("login")
    )


# =========================================================
# PASSWORD HASH UPDATE
# =========================================================

def update_user_password(
    user,
    password,
):

    user["password_hash"] = generate_password_hash(
        password
    )

    user["must_change_password"] = False


# =========================================================
# MONEY
# =========================================================

def money(value):

    try:
        return round(
            float(value),
            2,
        )
    except (
        TypeError,
        ValueError,
    ):
        return 0.0


# =========================================================
# EXPENSE PREPARATION
# =========================================================

def prepare_expense(expense):

    result = dict(expense)

    result["amount"] = money(
        result.get("amount", 0)
    )

    shared_by = result.get(
        "shared_by",
        [],
    )

    if not isinstance(
        shared_by,
        list,
    ):
        shared_by = []

    result["shared_by"] = shared_by

    return result


# =========================================================
# MEMBER CONTRIBUTIONS
# =========================================================

def get_member_contributions(
    members,
    settings,
):
    """
    Individual contribution per member.

    Backward compatible: if the old single-value settings
    (contribution_collected + contribution_by) exist and no
    per-member data has been saved yet, the whole amount is
    assigned to contribution_by.
    """

    stored = settings.get(
        "member_contributions"
    )

    contributions = {
        member: 0.0
        for member in members
    }

    if isinstance(stored, dict) and stored:

        for member in members:
            contributions[member] = money(
                stored.get(
                    member,
                    0,
                )
            )

        return contributions

    legacy_amount = money(
        settings.get(
            "contribution_collected",
            0,
        )
    )

    legacy_member = settings.get(
        "contribution_by",
        "",
    )

    if legacy_amount > 0 and legacy_member in contributions:
        contributions[legacy_member] = legacy_amount

    return contributions


# =========================================================
# FINANCIAL CALCULATIONS
# =========================================================

def calculate_financials(
    members,
    expenses,
    settings,
):

    member_paid = {
        member: 0.0
        for member in members
    }

    member_shared = {
        member: 0.0
        for member in members
    }

    category_totals = {}

    vehicle_totals = {}

    total = 0.0

    for expense in expenses:

        expense = prepare_expense(
            expense
        )

        amount = money(
            expense.get(
                "amount",
                0,
            )
        )

        total += amount

        paid_by = expense.get(
            "paid_by"
        )

        if paid_by in member_paid:
            member_paid[paid_by] += amount

        category = expense.get(
            "category",
            "Other",
        )

        category_totals[category] = (
            category_totals.get(
                category,
                0.0,
            )
            + amount
        )

        vehicle = expense.get(
            "vehicle",
            "",
        )

        if vehicle:

            vehicle_totals[vehicle] = (
                vehicle_totals.get(
                    vehicle,
                    0.0,
                )
                + amount
            )

        shared_by = expense.get(
            "shared_by",
            [],
        )

        if not shared_by:
            shared_by = members

        valid_shared = [
            member
            for member in shared_by
            if member in members
        ]

        if valid_shared:

            share = (
                amount
                / len(valid_shared)
            )

            for member in valid_shared:
                member_shared[member] += share

    member_contribution = get_member_contributions(
        members,
        settings,
    )

    contribution_collected = money(
        sum(member_contribution.values())
    )

    contributors_count = sum(
        1
        for value in member_contribution.values()
        if value > 0
    )

    remaining = (
        contribution_collected
        - total
    )

    normal_final_share = member_shared.copy()

    custom_final_shares = settings.get(
        "custom_final_shares",
        {},
    )

    final_share = {}

    for member in members:

        if member in custom_final_shares:

            final_share[member] = money(
                custom_final_shares[member]
            )

        else:

            final_share[member] = money(
                normal_final_share.get(
                    member,
                    0,
                )
            )

    balances = {}

    for member in members:

        balances[member] = money(
            member_contribution.get(
                member,
                0,
            )
            + member_paid.get(
                member,
                0,
            )
            - final_share.get(
                member,
                0,
            )
        )

    return {
        "total": money(total),
        "contribution_collected": contribution_collected,
        "remaining": money(remaining),
        "member_contribution": member_contribution,
        "contributors_count": contributors_count,
        "member_paid": member_paid,
        "member_shared": member_shared,
        "normal_final_share": normal_final_share,
        "final_share": final_share,
        "balances": balances,
        "category_totals": category_totals,
        "vehicle_totals": vehicle_totals,
    }


# =========================================================
# SETTLEMENT
# =========================================================

def build_settlements(
    members,
    balances,
):

    creditors = []
    debtors = []

    for member in members:

        balance = money(
            balances.get(
                member,
                0,
            )
        )

        if balance > 0.01:

            creditors.append(
                {
                    "member": member,
                    "amount": balance,
                }
            )

        elif balance < -0.01:

            debtors.append(
                {
                    "member": member,
                    "amount": abs(balance),
                }
            )

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

        amount = min(
            creditor["amount"],
            debtor["amount"],
        )

        amount = money(amount)

        if amount > 0:

            settlements.append(
                {
                    "from": debtor["member"],
                    "to": creditor["member"],
                    "amount": amount,
                }
            )

        creditor["amount"] = money(
            creditor["amount"]
            - amount
        )

        debtor["amount"] = money(
            debtor["amount"]
            - amount
        )

        if creditor["amount"] <= 0.01:
            creditor_index += 1

        if debtor["amount"] <= 0.01:
            debtor_index += 1

    return settlements


# =========================================================
# MAIN DASHBOARD
# =========================================================

@app.route("/")
@login_required
def index():

    members = load_members()
    settings = load_settings()
    expenses = load_expenses()

    expenses = [
        prepare_expense(expense)
        for expense in expenses
    ]

    financials = calculate_financials(
        members,
        expenses,
        settings,
    )

    settlements = build_settlements(
        members,
        financials["balances"],
    )

    selected_date = request.args.get(
        "date",
        settings.get(
            "trip_date",
            date.today().isoformat(),
        ),
    )

    daily_expenses = [
        expense
        for expense in expenses
        if expense.get("date") == selected_date
    ]

    daily_total = money(
        sum(
            money(
                expense.get(
                    "amount",
                    0,
                )
            )
            for expense in daily_expenses
        )
    )

    now = datetime.now()

    current_hour = now.strftime(
        "%I"
    )

    current_minute = now.strftime(
        "%M"
    )

    current_ampm = now.strftime(
        "%p"
    )

    current_user = get_current_user()

    return render_template(
        "index.html",
        members=members,
        settings=settings,
        expenses=expenses,
        financials=financials,
        settlements=settlements,
        daily_expenses=daily_expenses,
        daily_total=daily_total,
        selected_date=selected_date,
        categories=CATEGORIES,
        vehicles=VEHICLES,
        current_hour=current_hour,
        current_minute=current_minute,
        current_ampm=current_ampm,
        current_user=current_user,
        can_write=has_write_access(),
        is_admin=is_admin(),
    )


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/dashboard")
@admin_required
def dashboard():

    members = load_members()
    users = load_users()

    user_map = {
        user.get("member"): user
        for user in users
    }

    member_users = []

    for member in members:

        user = user_map.get(
            member
        )

        if user is None:

            username = make_unique_username(
                member,
                users,
            )

            user = {
                "username": username,
                "member": member,
                "access": "read",
                "enabled": True,
                "must_change_password": True,
            }

        member_users.append(
            user
        )

    return render_template(
        "dashboard.html",
        members=members,
        users=member_users,
        current_user=get_current_user(),
    )


# =========================================================
# ADMIN USER UPDATE
# =========================================================

@app.route(
    "/dashboard/update-user",
    methods=["POST"],
)
@admin_required
def dashboard_update_user():

    member = request.form.get(
        "member",
        "",
    ).strip()

    username = request.form.get(
        "username",
        "",
    ).strip()

    access = request.form.get(
        "access",
        "read",
    ).strip().lower()

    enabled = (
        request.form.get(
            "enabled"
        )
        == "on"
    )

    password = request.form.get(
        "password",
        "",
    )

    if not member:
        flash(
            "Member is required.",
            "error",
        )

        return redirect(
            url_for("dashboard")
        )

    if not username:
        flash(
            "Username cannot be empty.",
            "error",
        )

        return redirect(
            url_for("dashboard")
        )

    if access not in (
        "read",
        "write",
    ):
        access = "read"

    users = load_users()

    target_user = None

    for user in users:

        if user.get("member") == member:
            target_user = user
            break

    if target_user is None:

        target_user = {
            "member": member,
            "username": username,
            "password_hash": generate_password_hash(
                "change-me"
            ),
            "access": access,
            "enabled": enabled,
            "must_change_password": True,
        }

        users.append(
            target_user
        )

    else:

        for user in users:

            if (
                user is not target_user
                and user.get("username", "").lower()
                == username.lower()
            ):

                flash(
                    "Username is already in use.",
                    "error",
                )

                return redirect(
                    url_for("dashboard")
                )

        target_user["username"] = username
        target_user["access"] = access
        target_user["enabled"] = enabled

        if password:

            if len(password) < 6:

                flash(
                    "Password must contain at least 6 characters.",
                    "error",
                )

                return redirect(
                    url_for("dashboard")
                )

            update_user_password(
                target_user,
                password,
            )

    save_json(
        USERS_FILE,
        users,
    )

    flash(
        f"Access settings updated for {member}.",
        "success",
    )

    return redirect(
        url_for("dashboard")
    )


# =========================================================
# ADD EXPENSE
# =========================================================

@app.route(
    "/add_expense",
    methods=["POST"],
)
@write_required
def add_expense():

    members = load_members()

    date_value = request.form.get(
        "date",
        date.today().isoformat(),
    )

    hour = request.form.get(
        "hour",
        "",
    )

    minute = request.form.get(
        "minute",
        "",
    )

    ampm = request.form.get(
        "ampm",
        "",
    )

    category = request.form.get(
        "category",
        "Other",
    )

    amount = money(
        request.form.get(
            "amount",
            0,
        )
    )

    paid_by = request.form.get(
        "paid_by",
        "",
    )

    vehicle = request.form.get(
        "vehicle",
        "",
    )

    location = request.form.get(
        "location",
        "",
    ).strip()

    description = request.form.get(
        "description",
        "",
    ).strip()

    shared_by = request.form.getlist(
        "shared_by"
    )

    shared_by = [
        member
        for member in shared_by
        if member in members
    ]

    if not shared_by:
        shared_by = members.copy()

    if amount <= 0:

        flash(
            "Expense amount must be greater than zero.",
            "error",
        )

        return redirect(
            url_for("index")
        )

    if paid_by not in members:

        flash(
            "Invalid member selected for Paid By.",
            "error",
        )

        return redirect(
            url_for("index")
        )

    if category not in CATEGORIES:

        category = "Other"

    if category not in (
        "Fuel",
        "Toll",
    ):

        vehicle = ""

    expense = {
        "id": uuid.uuid4().hex,
        "date": date_value,
        "hour": hour,
        "minute": minute,
        "ampm": ampm,
        "category": category,
        "amount": amount,
        "paid_by": paid_by,
        "vehicle": vehicle,
        "location": location,
        "description": description,
        "shared_by": shared_by,
        "created_by": session.get(
            "username"
        ),
        "created_at": datetime.now().isoformat(),
    }

    expenses = load_expenses()

    expenses.append(
        expense
    )

    save_json(
        EXPENSES_FILE,
        expenses,
    )

    flash(
        "Expense added successfully.",
        "success",
    )

    return redirect(
        url_for(
            "index",
            date=date_value,
        )
    )


# =========================================================
# DELETE EXPENSE
# =========================================================

@app.route(
    "/delete_expense/<expense_id>",
    methods=["POST"],
)
@write_required
def delete_expense(expense_id):

    expenses = load_expenses()

    original_count = len(
        expenses
    )

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

    else:

        save_json(
            EXPENSES_FILE,
            expenses,
        )

        flash(
            "Expense deleted.",
            "success",
        )

    return redirect(
        url_for("index")
    )


# =========================================================
# UPDATE SETTINGS
# =========================================================

@app.route(
    "/update_settings",
    methods=["POST"],
)
@write_required
def update_settings():

    settings = load_settings()

    settings["trip_date"] = request.form.get(
        "trip_date",
        date.today().isoformat(),
    )

    members = load_members()

    member_contributions = {}

    for member in members:

        raw_value = request.form.get(
            "contribution_" + member,
            "",
        ).strip()

        amount = money(raw_value) if raw_value else 0.0

        if amount < 0:

            flash(
                f"Contribution cannot be negative for {member}.",
                "error",
            )

            return redirect(
                url_for("index")
            )

        member_contributions[member] = amount

    settings["member_contributions"] = member_contributions

    settings["contribution_collected"] = money(
        sum(member_contributions.values())
    )

    save_json(
        SETTINGS_FILE,
        settings,
    )

    flash(
        "Trip settings updated.",
        "success",
    )

    return redirect(
        url_for("index")
    )


# =========================================================
# UPDATE MEMBERS
# =========================================================

@app.route(
    "/update_members",
    methods=["POST"],
)
@admin_required
def update_members():

    members = []

    for index in range(1, 9):

        member = request.form.get(
            f"member_{index}",
            "",
        ).strip()

        if member:
            members.append(
                member
            )

    if not members:

        flash(
            "At least one member is required.",
            "error",
        )

        return redirect(
            url_for("index")
        )

    if len(members) != len(set(members)):

        flash(
            "Member names must be unique.",
            "error",
        )

        return redirect(
            url_for("index")
        )

    save_json(
        MEMBERS_FILE,
        members,
    )

    synchronize_users()

    flash(
        "Members updated.",
        "success",
    )

    return redirect(
        url_for("index")
    )


# =========================================================
# CUSTOM SPLIT
# =========================================================

@app.route(
    "/custom_split",
    methods=["POST"],
)
@write_required
def custom_split():

    members = load_members()
    settings = load_settings()

    custom_shares = {}

    for member in members:

        field_name = (
            "share_"
            + member
        )

        value = request.form.get(
            field_name,
            "",
        ).strip()

        if value:

            try:
                amount = float(value)
            except ValueError:

                flash(
                    f"Invalid share for {member}.",
                    "error",
                )

                return redirect(
                    url_for("index")
                )

            if amount < 0:

                flash(
                    f"Share cannot be negative for {member}.",
                    "error",
                )

                return redirect(
                    url_for("index")
                )

            custom_shares[member] = money(
                amount
            )

    settings["custom_final_shares"] = (
        custom_shares
    )

    save_json(
        SETTINGS_FILE,
        settings,
    )

    flash(
        "Custom final split saved.",
        "success",
    )

    return redirect(
        url_for("index")
    )


# =========================================================
# CLEAR CUSTOM SPLIT
# =========================================================

@app.route(
    "/clear_custom_split",
    methods=["POST"],
)
@write_required
def clear_custom_split():

    settings = load_settings()

    settings["custom_final_shares"] = {}

    save_json(
        SETTINGS_FILE,
        settings,
    )

    flash(
        "Custom final split cleared.",
        "success",
    )

    return redirect(
        url_for("index")
    )


# =========================================================
# HEALTH
# =========================================================

@app.route("/api/health")
def health():

    return jsonify(
        {
            "status": "ok",
            "application": "Trip Expense Tracker",
            "logged_in": bool(
                session.get("logged_in")
            ),
        }
    )


# =========================================================
# CONFIG
# =========================================================

@app.route("/api/config")
@login_required
def api_config():

    return jsonify(
        {
            "hostname": APP_HOSTNAME,
            "public_url": PUBLIC_URL,
            "user": get_current_user(),
            "can_write": has_write_access(),
            "is_admin": is_admin(),
        }
    )


# =========================================================
# START APPLICATION
# =========================================================

if __name__ == "__main__":

    ensure_data_files()

    print()
    print("=" * 60)
    print("Trip Expense Tracker")
    print("=" * 60)

    print(
        f"Local:      http://127.0.0.1:{PORT}"
    )

    print(
        f"LAN:        http://<YOUR-LAN-IP>:{PORT}"
    )

    if APP_HOSTNAME:
        print(
            f"Hostname:   https://{APP_HOSTNAME}"
        )

    if PUBLIC_URL:
        print(
            f"Public URL: {PUBLIC_URL}"
        )

    print("=" * 60)
    print()

    app.run(
        host=HOST,
        port=PORT,
        debug=DEBUG,
    )