"""Centralized environment-based configuration for the backend service.

Keeping all environment parsing in one file makes it easy for beginners
to discover what can be configured and where defaults come from.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path

from dotenv import load_dotenv

# Load `.env` values so local development works out of the box.
load_dotenv()

# Project root directory (one level above `backend/`).
PROJECT_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class AppSettings:
    """Runtime settings used across API routes and Stripe services."""

    stripe_secret_key: str
    stripe_webhook_secret: str | None
    database_url: str
    frontend_base_url: str
    frontend_origins: list[str]
    default_currency: str
    default_product_name: str
    default_amount_cents: int
    default_quantity: int
    max_amount_cents: int
    max_quantity: int
    api_title: str
    api_version: str


def _require_env(name: str) -> str:
    """Read a required environment variable and raise a clear error if missing."""

    value = os.getenv(name)
    if value:
        return value

    raise RuntimeError(f"Missing required environment variable: {name}")


def _read_int_env(name: str, default: int) -> int:
    """Read an integer environment variable with a safe fallback value."""

    raw_value = os.getenv(name)
    if raw_value is None or raw_value.strip() == "":
        return default

    try:
        return int(raw_value)
    except ValueError as error:
        raise RuntimeError(f"Environment variable {name} must be a valid integer.") from error


def _read_origins_env(name: str, default: str) -> list[str]:
    """Parse a comma-separated CORS origin list into a clean string list."""

    raw_origins = os.getenv(name, default)
    origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]

    if not origins:
        return ["http://localhost:3000"]

    return origins


def _default_sqlite_url() -> str:
    """Build default SQLite URL using an absolute project-root file path."""

    sqlite_file = (PROJECT_ROOT / "stripe_payments.db").resolve()
    return f"sqlite:///{sqlite_file}"


def _normalize_database_url(database_url: str) -> str:
    """Normalize DB URL so relative SQLite paths resolve to project root.

    This prevents accidental creation of multiple SQLite files when
    uvicorn is started from different working directories.
    """

    if not database_url.startswith("sqlite:///"):
        return database_url

    raw_path = database_url.removeprefix("sqlite:///")
    if raw_path.startswith("/"):
        return database_url

    normalized_path = (PROJECT_ROOT / raw_path).resolve()
    return f"sqlite:///{normalized_path}"


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Load settings once and share them across the whole application.

    Caching avoids re-reading environment variables on every request.
    """

    return AppSettings(
        stripe_secret_key=_require_env("STRIPE_SECRET_KEY"),
        stripe_webhook_secret=os.getenv("STRIPE_WEBHOOK_SECRET"),
        database_url=_normalize_database_url(
            os.getenv("DATABASE_URL", _default_sqlite_url())
        ),
        frontend_base_url=os.getenv("FRONTEND_BASE_URL", "http://localhost:3000").rstrip("/"),
        frontend_origins=_read_origins_env("FRONTEND_ORIGINS", "http://localhost:3000"),
        default_currency=os.getenv("DEFAULT_CURRENCY", "usd").lower(),
        default_product_name=os.getenv("DEFAULT_PRODUCT_NAME", "Demo Product"),
        default_amount_cents=_read_int_env("DEFAULT_AMOUNT_CENTS", 1000),
        default_quantity=_read_int_env("DEFAULT_QUANTITY", 1),
        max_amount_cents=_read_int_env("MAX_AMOUNT_CENTS", 1_000_000),
        max_quantity=_read_int_env("MAX_QUANTITY", 100),
        api_title=os.getenv("API_TITLE", "Stripe Checkout Demo API"),
        api_version=os.getenv("API_VERSION", "2.0.0"),
    )
