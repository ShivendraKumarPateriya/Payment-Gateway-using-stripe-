"""Route module exports for easier app inclusion."""

from backend.app.api.routes.checkout import router as checkout_router

__all__ = ["checkout_router"]
