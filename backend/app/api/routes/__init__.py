"""Route module exports for easier app inclusion."""

from backend.app.api.routes.checkout import router as checkout_router
from backend.app.api.routes.orders import router as orders_router
from backend.app.api.routes.webhooks import router as webhooks_router

__all__ = ["checkout_router", "orders_router", "webhooks_router"]
