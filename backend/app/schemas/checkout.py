"""Pydantic schema models for checkout and payment endpoints.

These classes define and validate the JSON shape exchanged between
frontend and backend.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class CheckoutItemPayload(BaseModel):
    """Single purchasable item sent by the frontend.

    Stripe Checkout requires amount and currency in the smallest unit,
    for example USD cents.
    """

    product_name: str = Field(
        ...,
        min_length=2,
        max_length=120,
        description="Human-readable product name shown during checkout.",
    )
    unit_amount: int = Field(
        ...,
        gt=0,
        description="Price in smallest currency unit (for USD, cents).",
        examples=[1000],
    )
    quantity: int = Field(
        1,
        gt=0,
        le=100,
        description="How many units should be charged in one checkout session.",
    )
    currency: str = Field(
        "usd",
        min_length=3,
        max_length=3,
        description="Three-letter ISO currency code such as usd or eur.",
    )
    description: str | None = Field(
        None,
        max_length=400,
        description="Optional description shown in payment tools and dashboards.",
    )

    @field_validator("product_name")
    @classmethod
    def validate_product_name(cls, value: str) -> str:
        """Strip whitespace and block blank product names."""

        normalized = value.strip()
        if not normalized:
            raise ValueError("product_name cannot be blank.")

        return normalized

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        """Normalize incoming currency code to lowercase."""

        return value.lower().strip()

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        """Trim optional description text and convert empty strings to None."""

        if value is None:
            return None

        normalized = value.strip()
        return normalized or None


class CheckoutSessionCreateRequest(BaseModel):
    """Payload used to create a Stripe Checkout Session."""

    item: CheckoutItemPayload = Field(
        ..., description="Item details that Stripe should charge for."
    )
    success_path: str = Field(
        "/success",
        description="Frontend path where Stripe redirects after successful payment.",
    )
    cancel_path: str = Field(
        "/cancel",
        description="Frontend path where Stripe redirects when payment is cancelled.",
    )
    customer_email: str | None = Field(
        None,
        description="Optional customer email to prefill in Checkout.",
    )
    allow_promotion_codes: bool = Field(
        True,
        description="Allow coupon/promo code input on hosted checkout page.",
    )

    @field_validator("success_path", "cancel_path")
    @classmethod
    def validate_paths(cls, value: str) -> str:
        """Allow only local frontend paths, not full external URLs."""

        normalized = value.strip()
        if not normalized.startswith("/"):
            raise ValueError("Path values must start with '/'.")

        if normalized.startswith("//"):
            raise ValueError("Path values cannot start with '//'.")

        return normalized


class CheckoutSessionResponse(BaseModel):
    """Minimal response required by frontend to redirect user to Stripe."""

    id: str = Field(..., description="Stripe Checkout Session ID.")
    url: str = Field(..., description="Stripe hosted checkout URL.")


class PaymentIntentCreateRequest(BaseModel):
    """Payload for creating a PaymentIntent when using custom card forms."""

    amount: int = Field(
        ...,
        gt=0,
        description="Amount in smallest currency unit, such as cents.",
    )
    currency: str = Field(
        "usd",
        min_length=3,
        max_length=3,
        description="Three-letter ISO currency code.",
    )

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        """Normalize currency input to lowercase."""

        return value.lower().strip()


class PaymentIntentResponse(BaseModel):
    """Response payload used by Stripe Elements confirmation methods."""

    clientSecret: str = Field(..., description="Client secret used by Stripe.js.")


class CheckoutDefaultsResponse(BaseModel):
    """Default checkout values exposed by backend for frontend initialization."""

    product_name: str = Field(..., description="Default product name.")
    unit_amount: int = Field(..., description="Default amount in smallest currency unit.")
    quantity: int = Field(..., description="Default quantity.")
    currency: str = Field(..., description="Default currency code.")
