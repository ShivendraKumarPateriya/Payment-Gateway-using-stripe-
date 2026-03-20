"""API routes related to creating Stripe checkout and payment sessions."""

from __future__ import annotations

import stripe
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core import AppSettings, get_settings
from backend.app.db import get_db_session
from backend.app.schemas import (
    CheckoutDefaultsResponse,
    CheckoutItemPayload,
    CheckoutSessionCreateRequest,
    CheckoutSessionResponse,
    PaymentIntentCreateRequest,
    PaymentIntentResponse,
)
from backend.app.services import StripeCheckoutService

router = APIRouter(tags=["Payments"])


def _stripe_error_message(error: stripe.StripeError) -> str:
    """Return a safe error message that can be shown to frontend users."""

    return error.user_message or "Stripe request failed. Please check your input or try again."


def _default_checkout_request(settings: AppSettings) -> CheckoutSessionCreateRequest:
    """Build default checkout payload used when frontend sends an empty body."""

    return CheckoutSessionCreateRequest(
        item=CheckoutItemPayload(
            product_name=settings.default_product_name,
            unit_amount=settings.default_amount_cents,
            quantity=settings.default_quantity,
            currency=settings.default_currency,
        ),
        success_path="/success",
        cancel_path="/cancel",
    )


def _default_payment_intent_request(settings: AppSettings) -> PaymentIntentCreateRequest:
    """Build default PaymentIntent payload for backwards compatibility."""

    return PaymentIntentCreateRequest(
        amount=settings.default_amount_cents,
        currency=settings.default_currency,
    )


@router.get("/health")
def healthcheck() -> dict[str, str]:
    """Simple health endpoint to verify the backend server is running."""

    return {"status": "ok"}


@router.get("/checkout-defaults", response_model=CheckoutDefaultsResponse)
def checkout_defaults(settings: AppSettings = Depends(get_settings)) -> CheckoutDefaultsResponse:
    """Return backend defaults so frontend can prefill the checkout form."""

    return CheckoutDefaultsResponse(
        product_name=settings.default_product_name,
        unit_amount=settings.default_amount_cents,
        quantity=settings.default_quantity,
        currency=settings.default_currency,
    )


@router.post("/create-checkout-session", response_model=CheckoutSessionResponse)
def create_checkout_session(
    payload: CheckoutSessionCreateRequest | None = Body(default=None),
    settings: AppSettings = Depends(get_settings),
    db_session: Session = Depends(get_db_session),
) -> CheckoutSessionResponse:
    """Create a Stripe-hosted checkout session from frontend-provided data.

    If no body is sent, the backend falls back to environment defaults so
    beginners can still test quickly.
    """

    checkout_payload = payload or _default_checkout_request(settings)
    service = StripeCheckoutService(settings)

    try:
        return service.create_checkout_session(checkout_payload, db_session)
    except ValueError as error:
        db_session.rollback()
        raise HTTPException(status_code=400, detail=str(error)) from error
    except stripe.StripeError as error:
        db_session.rollback()
        raise HTTPException(status_code=502, detail=_stripe_error_message(error)) from error
    except Exception as error:
        db_session.rollback()
        raise HTTPException(status_code=500, detail="Unexpected server error.") from error


@router.post("/create-payment-intent", response_model=PaymentIntentResponse)
def create_payment_intent(
    payload: PaymentIntentCreateRequest | None = Body(default=None),
    settings: AppSettings = Depends(get_settings),
) -> PaymentIntentResponse:
    """Create a Stripe PaymentIntent for custom Elements card flows."""

    payment_payload = payload or _default_payment_intent_request(settings)
    service = StripeCheckoutService(settings)

    try:
        return service.create_payment_intent(payment_payload)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except stripe.StripeError as error:
        raise HTTPException(status_code=502, detail=_stripe_error_message(error)) from error
