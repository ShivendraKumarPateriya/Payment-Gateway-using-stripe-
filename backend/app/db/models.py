"""Database models for orders and Stripe webhook event logs."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class OrderStatus(str, Enum):
    """Allowed order states managed by checkout + webhook lifecycle."""

    CREATED = "created"
    PENDING = "pending"
    PAID = "paid"
    PAYMENT_FAILED = "payment_failed"
    EXPIRED = "expired"


class Order(Base):
    """Represents one checkout order persisted before Stripe redirect."""

    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    status: Mapped[str] = mapped_column(
        String(32), default=OrderStatus.CREATED.value, index=True, nullable=False
    )

    product_name: Mapped[str] = mapped_column(String(120), nullable=False)
    unit_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    total_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    customer_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    checkout_session_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True, nullable=True
    )
    payment_intent_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True, nullable=True
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    webhook_events: Mapped[list["StripeWebhookEvent"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class StripeWebhookEvent(Base):
    """Stores processed Stripe events to enforce idempotent webhook handling."""

    __tablename__ = "stripe_webhook_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stripe_event_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    api_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    livemode: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    order_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True
    )
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    order: Mapped[Order | None] = relationship(back_populates="webhook_events")
