"""Stripe webhook processing logic with idempotent database updates."""

from __future__ import annotations

from datetime import datetime, timezone

import stripe
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db import Order, OrderStatus, StripeWebhookEvent


class StripeWebhookService:
    """Processes Stripe webhook events and updates local order state safely."""

    def process_event(self, event: stripe.Event, db_session: Session) -> tuple[bool, str]:
        """Process one webhook event idempotently.

        Returns:
            tuple[bool, str]: (is_duplicate, stripe_event_id)
        """

        event_id = event["id"]
        event_type = event["type"]

        duplicate_event = db_session.scalar(
            select(StripeWebhookEvent).where(StripeWebhookEvent.stripe_event_id == event_id)
        )
        if duplicate_event is not None:
            return True, event_id

        event_object = event["data"]["object"]
        order = self._find_order_for_event(db_session, event_object)

        if order is not None:
            self._apply_order_updates(order, event_type, event_object)
            db_session.add(order)

        event_log = StripeWebhookEvent(
            stripe_event_id=event_id,
            event_type=event_type,
            api_version=event.get("api_version"),
            livemode=bool(event.get("livemode", False)),
            order_id=order.id if order else None,
            payload_json=event.to_dict_recursive(),
            processing_error=None,
        )

        db_session.add(event_log)
        db_session.commit()
        return False, event_id

    def _find_order_for_event(self, db_session: Session, event_object: dict) -> Order | None:
        """Resolve local order row from Stripe object identifiers."""

        metadata = event_object.get("metadata") or {}

        order_id = metadata.get("order_id") or event_object.get("client_reference_id")
        if order_id:
            order = db_session.get(Order, order_id)
            if order:
                return order

        checkout_session_id = event_object.get("id")
        if checkout_session_id and str(checkout_session_id).startswith("cs_"):
            order = db_session.scalar(
                select(Order).where(Order.checkout_session_id == checkout_session_id)
            )
            if order:
                return order

        payment_intent_id = event_object.get("payment_intent") or event_object.get("id")
        if payment_intent_id and str(payment_intent_id).startswith("pi_"):
            order = db_session.scalar(select(Order).where(Order.payment_intent_id == payment_intent_id))
            if order:
                return order

        return None

    def _apply_order_updates(self, order: Order, event_type: str, event_object: dict) -> None:
        """Apply webhook event details to a local order object."""

        payment_intent = event_object.get("payment_intent")
        customer_id = event_object.get("customer")

        if payment_intent:
            order.payment_intent_id = payment_intent
        if customer_id:
            order.stripe_customer_id = customer_id

        if event_type == "checkout.session.completed":
            payment_status = event_object.get("payment_status")
            if payment_status in {"paid", "no_payment_required"}:
                self._set_order_paid(order)
            else:
                self._set_order_pending(order)
            return

        if event_type == "checkout.session.async_payment_succeeded":
            self._set_order_paid(order)
            return

        if event_type == "checkout.session.async_payment_failed":
            self._set_order_failed(order, "Asynchronous payment failed.")
            return

        if event_type == "checkout.session.expired":
            self._set_order_expired(order)
            return

        if event_type == "payment_intent.payment_failed":
            last_payment_error = event_object.get("last_payment_error") or {}
            message = last_payment_error.get("message") or "Payment intent failed."
            self._set_order_failed(order, message)

    def _set_order_paid(self, order: Order) -> None:
        """Mark an order as paid (terminal success state)."""

        order.status = OrderStatus.PAID.value
        order.failure_reason = None
        if order.paid_at is None:
            order.paid_at = datetime.now(timezone.utc)

    def _set_order_pending(self, order: Order) -> None:
        """Mark an order as pending unless already paid."""

        if order.status == OrderStatus.PAID.value:
            return
        order.status = OrderStatus.PENDING.value

    def _set_order_failed(self, order: Order, reason: str) -> None:
        """Mark an order as failed unless already paid."""

        if order.status == OrderStatus.PAID.value:
            return
        order.status = OrderStatus.PAYMENT_FAILED.value
        order.failure_reason = reason

    def _set_order_expired(self, order: Order) -> None:
        """Mark an order as expired unless already in terminal paid state."""

        if order.status == OrderStatus.PAID.value:
            return
        order.status = OrderStatus.EXPIRED.value
