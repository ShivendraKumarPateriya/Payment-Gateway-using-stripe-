"""Read-only API routes for checking persisted order/payment state."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core import AppSettings, get_settings
from backend.app.db import Order, get_db_session
from backend.app.schemas import OrderResponse
from backend.app.services import OrderService

router = APIRouter(prefix="/orders", tags=["Orders"])


def _to_order_response(order: Order) -> OrderResponse:
    """Convert ORM order model to API response schema."""

    return OrderResponse(
        id=order.id,
        status=order.status,
        product_name=order.product_name,
        unit_amount=order.unit_amount,
        quantity=order.quantity,
        total_amount=order.total_amount,
        currency=order.currency,
        description=order.description,
        customer_email=order.customer_email,
        checkout_session_id=order.checkout_session_id,
        payment_intent_id=order.payment_intent_id,
        stripe_customer_id=order.stripe_customer_id,
        failure_reason=order.failure_reason,
        paid_at=order.paid_at,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: str,
    settings: AppSettings = Depends(get_settings),
    db_session: Session = Depends(get_db_session),
) -> OrderResponse:
    """Fetch one order by internal order ID."""

    order = db_session.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found.")

    order_service = OrderService(settings)
    order = order_service.sync_order_from_stripe(order, db_session)

    return _to_order_response(order)


@router.get("/by-session/{checkout_session_id}", response_model=OrderResponse)
def get_order_by_checkout_session(
    checkout_session_id: str,
    settings: AppSettings = Depends(get_settings),
    db_session: Session = Depends(get_db_session),
) -> OrderResponse:
    """Fetch one order using Stripe Checkout Session ID from success URL."""

    order = db_session.scalar(
        select(Order).where(Order.checkout_session_id == checkout_session_id)
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found for this session.")

    order_service = OrderService(settings)
    order = order_service.sync_order_from_stripe(order, db_session)

    return _to_order_response(order)
