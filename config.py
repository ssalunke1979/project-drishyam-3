import os

from dotenv import load_dotenv


load_dotenv()


HOST = os.getenv(
    "FLASK_HOST",
    "0.0.0.0"
)

PORT = int(
    os.getenv(
        "FLASK_PORT",
        "5000"
    )
)

DEBUG = (
    os.getenv(
        "FLASK_DEBUG",
        "false"
    ).lower()
    == "true"
)

SECRET_KEY = os.getenv(
    "FLASK_SECRET_KEY",
    "change-this-secret-key"
)

APP_HOSTNAME = os.getenv(
    "APP_HOSTNAME",
    ""
).strip()

PUBLIC_URL = os.getenv(
    "FLASK_PUBLIC_URL",
    ""
).strip().rstrip("/")


# =========================================================
# ADMIN LOGIN
# =========================================================

DASHBOARD_USERNAME = os.getenv(
    "DASHBOARD_USERNAME",
    "admin"
).strip()

DASHBOARD_PASSWORD = os.getenv(
    "DASHBOARD_PASSWORD",
    "change-me"
)


# =========================================================
# SESSION
# =========================================================

SESSION_COOKIE_SECURE = (
    os.getenv(
        "SESSION_COOKIE_SECURE",
        "false"
    ).lower()
    == "true"
)

SESSION_COOKIE_HTTPONLY = (
    os.getenv(
        "SESSION_COOKIE_HTTPONLY",
        "true"
    ).lower()
    == "true"
)

SESSION_COOKIE_SAMESITE = os.getenv(
    "SESSION_COOKIE_SAMESITE",
    "Lax"
)