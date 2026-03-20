"""Order read/synchronization service for status checks after checkout."""

from __future__ import annotations

from datetime import datetime, timezone

import stripe
from sqlalchemy.orm import Session

from backend.app.core import AppSettings
from backend.app.db import Order, OrderStatus


class OrderService:
    """Provides order lookup and optional Stripe reconciliation helpers."""

    def __init__(self, settings: AppSettings) -> None:
        """Initialize service with Stripe credentials."""

        self.settings = settings
        stripe.api_key = settings.stripe_secret_key

    def sync_order_from_stripe(self, order: Order, db_session: Session) -> Order:
        """Reconcile one order status with current Stripe Checkout Session state.

        Why this exists:
            Webhooks are the source of truth, but if webhook setup is missing,
            this read-time sync avoids permanently-stuck `pending` orders.
        """

        if not order.checkout_session_id:
            return order

        # No need to repeatedly sync terminal paid orders.
        if order.status == OrderStatus.PAID.value:
            return order

        try:
            session = stripe.checkout.Session.retrieve(order.checkout_session_id)
        except stripe.StripeError:
            # Keep current DB state unchanged when Stripe retrieval fails.
            return order

        changed = False

        payment_intent_id = session.get("payment_intent")
        customer_id = session.get("customer")
        payment_status = session.get("payment_status")
        checkout_status = session.get("status")

        if payment_intent_id and order.payment_intent_id != payment_intent_id:
            order.payment_intent_id = payment_intent_id
            changed = True

        if customer_id and order.stripe_customer_id != customer_id:
            order.stripe_customer_id = customer_id
            changed = True

        if payment_status in {"paid", "no_payment_required"}:
            if order.status != OrderStatus.PAID.value:
                order.status = OrderStatus.PAID.value
                if order.paid_at is None:
                    order.paid_at = datetime.now(timezone.utc)
                order.failure_reason = None
                changed = True
        elif checkout_status == "expired":
            if order.status != OrderStatus.EXPIRED.value:
                order.status = OrderStatus.EXPIRED.value
                changed = True

        if changed:
            db_session.add(order)
            db_session.commit()
            db_session.refresh(order)

        return order


__all__ = ["OrderService"]
