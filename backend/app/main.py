"""FastAPI application setup and dependency wiring.

The app object exported here is the real ASGI application instance.
"""

from __future__ import annotations

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes import checkout_router, orders_router, webhooks_router
from backend.app.core import get_settings
from backend.app.db import Base, get_engine

# Load environment variables from the project .env file (if present).
load_dotenv()


def create_application() -> FastAPI:
    """Create and configure a FastAPI application instance."""

    settings = get_settings()

    app = FastAPI(
        title=settings.api_title,
        version=settings.api_version,
        description=(
            "A beginner-friendly Stripe checkout backend with clear schemas, "
            "service layer separation, and environment-driven configuration."
        ),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.frontend_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # For this educational project we create tables automatically.
    # In production, prefer Alembic migrations for schema changes.
    Base.metadata.create_all(bind=get_engine())

    app.include_router(checkout_router)
    app.include_router(orders_router)
    app.include_router(webhooks_router)
    return app


app = create_application()

__all__ = ["app", "create_application"]
