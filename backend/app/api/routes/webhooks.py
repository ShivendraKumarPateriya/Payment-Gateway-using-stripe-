"""Webhook endpoints for receiving and verifying Stripe event notifications."""

from __future__ import annotations

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from backend.app.core import AppSettings, get_settings
from backend.app.db import get_db_session
from backend.app.schemas import WebhookAckResponse
from backend.app.services import StripeWebhookService

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/stripe", response_model=WebhookAckResponse)
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
    settings: AppSettings = Depends(get_settings),
    db_session: Session = Depends(get_db_session),
) -> WebhookAckResponse:
    """Receive Stripe webhook, verify signature, and process event idempotently."""

    if not settings.stripe_webhook_secret:
        raise HTTPException(
            status_code=500,
            detail="STRIPE_WEBHOOK_SECRET is not configured on the server.",
        )

    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header.")

    payload_bytes = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload=payload_bytes,
            sig_header=stripe_signature,
            secret=settings.stripe_webhook_secret,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Invalid webhook payload.") from error
    except stripe.error.SignatureVerificationError as error:
        raise HTTPException(status_code=400, detail="Invalid webhook signature.") from error

    processor = StripeWebhookService()

    try:
        duplicate, event_id = processor.process_event(event, db_session)
    except Exception as error:
        db_session.rollback()
        raise HTTPException(status_code=500, detail="Webhook processing failed.") from error

    return WebhookAckResponse(received=True, duplicate=duplicate, event_id=event_id)
