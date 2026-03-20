"""Business logic layer for Stripe checkout and payment operations.

This file intentionally keeps Stripe-specific code out of API route functions,
so route handlers remain short and easier to follow.
"""

from __future__ import annotations

import stripe

from backend.app.core import AppSettings
from backend.app.schemas import (
    CheckoutSessionCreateRequest,
    CheckoutSessionResponse,
    PaymentIntentCreateRequest,
    PaymentIntentResponse,
)


class StripeCheckoutService:
    """Service object that wraps Stripe API calls used by this project."""

    def __init__(self, settings: AppSettings) -> None:
        """Initialize Stripe client configuration from application settings."""

        self.settings = settings
        stripe.api_key = settings.stripe_secret_key

    def create_checkout_session(
        self, payload: CheckoutSessionCreateRequest
    ) -> CheckoutSessionResponse:
        """Create a hosted Stripe Checkout Session from validated request data."""

        self._validate_amount(payload.item.unit_amount)
        self._validate_quantity(payload.item.quantity)

        success_url = self._build_success_url(payload.success_path)
        cancel_url = self._build_cancel_url(payload.cancel_path)

        session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": payload.item.currency,
                        "product_data": {
                            "name": payload.item.product_name,
                            "description": payload.item.description,
                        },
                        "unit_amount": payload.item.unit_amount,
                    },
                    "quantity": payload.item.quantity,
                }
            ],
            allow_promotion_codes=payload.allow_promotion_codes,
            customer_email=payload.customer_email,
            success_url=success_url,
            cancel_url=cancel_url,
        )

        if not session.url:
            raise RuntimeError("Stripe session URL was not returned by Stripe API.")

        return CheckoutSessionResponse(id=session.id, url=session.url)

    def create_payment_intent(
        self, payload: PaymentIntentCreateRequest
    ) -> PaymentIntentResponse:
        """Create a PaymentIntent for card-form based flows."""

        self._validate_amount(payload.amount)

        payment_intent = stripe.PaymentIntent.create(
            amount=payload.amount,
            currency=payload.currency,
            automatic_payment_methods={"enabled": True},
        )

        return PaymentIntentResponse(clientSecret=payment_intent.client_secret)

    def _build_frontend_url(self, path: str) -> str:
        """Join configured frontend base URL and path into one absolute URL."""

        cleaned_path = path if path.startswith("/") else f"/{path}"
        return f"{self.settings.frontend_base_url}{cleaned_path}"

    def _build_success_url(self, success_path: str) -> str:
        """Build success URL and attach Stripe session ID query parameter.

        The `{CHECKOUT_SESSION_ID}` placeholder is replaced by Stripe when
        the customer is redirected after payment.
        """

        success_url = self._build_frontend_url(success_path)
        separator = "&" if "?" in success_url else "?"
        return (
            f"{success_url}{separator}"
            "checkout_status=success&session_id={CHECKOUT_SESSION_ID}"
        )

    def _build_cancel_url(self, cancel_path: str) -> str:
        """Build cancel URL with a query parameter used by frontend page routing."""

        cancel_url = self._build_frontend_url(cancel_path)
        separator = "&" if "?" in cancel_url else "?"
        return f"{cancel_url}{separator}checkout_status=cancelled"

    def _validate_amount(self, amount: int) -> None:
        """Ensure amount is positive and does not exceed backend safety limit."""

        if amount > self.settings.max_amount_cents:
            raise ValueError(
                f"Amount exceeds max allowed value ({self.settings.max_amount_cents})."
            )

    def _validate_quantity(self, quantity: int) -> None:
        """Ensure quantity does not exceed backend safety limit."""

        if quantity > self.settings.max_quantity:
            raise ValueError(
                f"Quantity exceeds max allowed value ({self.settings.max_quantity})."
            )


__all__ = ["StripeCheckoutService"]
