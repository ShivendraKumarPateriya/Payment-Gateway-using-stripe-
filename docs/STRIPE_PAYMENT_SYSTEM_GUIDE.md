# Stripe Payment Gateway System Guide (Absolute Beginner Friendly)

This guide explains the complete project in simple language: what a payment gateway is, how this app works end-to-end, and how each feature maps to code.

## 1. What Is a Payment Gateway?

A payment gateway is the secure bridge between your app and the payment network.

In plain words:
- your app asks to charge a customer
- the payment gateway securely collects card/payment details
- it talks to banks/payment rails
- it tells your backend whether payment succeeded, failed, or is still pending

In this project, **Stripe** is the payment gateway provider.

## 2. Who Does What in This Project?

- **Frontend (React):** collects product + amount details from user and starts checkout.
- **Backend (FastAPI):** validates data, creates Stripe session, stores orders in DB.
- **Stripe Checkout Page:** hosted payment page where user completes payment.
- **Webhooks:** Stripe-to-backend server notifications for final payment status.
- **PostgreSQL/SQLite:** stores orders and processed webhook events.

## 3. Main Features Implemented

1. Dynamic checkout from form data (no hardcoded amount/product required).
2. Backend defaults endpoint for beginner-friendly prefilled form values.
3. Safe validation on both frontend and backend.
4. Hosted Stripe Checkout session creation.
5. Clean success and cancel UX pages.
6. Order status API by order ID and by Stripe session ID.
7. Webhook signature verification (security-critical).
8. Idempotent webhook processing (safe retries).
9. Persistent order + webhook tables in database.
10. Read-time Stripe reconciliation fallback for stuck `pending` orders.
11. Optional PaymentIntent endpoint for custom card-form learning.

## 4. Project Structure (Why It Is Organized This Way)

```text
backend/
  app/
    api/routes/
      checkout.py      # checkout + payment intent APIs
      orders.py        # order status APIs
      webhooks.py      # Stripe webhook API
    core/
      config.py        # environment settings
    db/
      base.py          # SQLAlchemy base
      models.py        # Order + StripeWebhookEvent models
      session.py       # engine/session helpers
    schemas/
      checkout.py      # request/response validation schemas
    services/
      stripe_checkout.py  # Stripe checkout business logic
      webhook_service.py  # webhook processing logic
      order_service.py    # status reconciliation logic
    main.py
  main.py

stripe-frontend/src/
  App.js
  config/environment.js
  services/checkoutApi.js
  components/checkout/
  pages/
  styles/checkout.css
```

## 5. End-to-End Payment Flow (Step by Step)

1. User fills checkout form on frontend.
2. Frontend sends `POST /create-checkout-session` with form payload.
3. Backend validates payload and creates an `orders` row with status `created`.
4. Backend creates Stripe Checkout Session and stores `checkout_session_id`.
5. Backend marks order `pending` and returns Stripe `url`.
6. Frontend redirects browser to Stripe hosted checkout page.
7. User pays on Stripe page.
8. Stripe redirects user back to frontend success page.
9. Stripe also sends webhook events to backend at `POST /webhooks/stripe`.
10. Backend verifies webhook signature and updates order status in DB.
11. Success page calls `GET /orders/by-session/{session_id}` to show real DB status.
12. If webhook did not arrive, order API performs Stripe reconciliation fallback and can update `pending` to `paid`.

## 6. Feature-by-Feature Working (With API + Code Mapping)

## 6.1 Checkout Form UI

What it does:
- lets user enter product name, amount, quantity, currency, email, description
- lets user enable/disable promo codes

Where:
- `stripe-frontend/src/components/checkout/CheckoutForm.js`

## 6.2 Frontend Payload Builder + Validation

What it does:
- parses numeric inputs safely
- checks required values
- enforces minimum total for some currencies (for example INR)
- sends clean payload shape expected by backend

Where:
- `stripe-frontend/src/App.js`

## 6.3 Backend Defaults for Frontend

What it does:
- returns default values from environment
- avoids hardcoded values in frontend

API:
- `GET /checkout-defaults`

Where:
- route: `backend/app/api/routes/checkout.py`
- settings source: `backend/app/core/config.py`

## 6.4 Create Checkout Session

What it does:
- validates amount/quantity/total
- creates local order row first
- creates Stripe Checkout Session with metadata (`order_id`)
- returns `session_id`, hosted `url`, and internal `order_id`

API:
- `POST /create-checkout-session`

Where:
- route: `backend/app/api/routes/checkout.py`
- service: `backend/app/services/stripe_checkout.py`

## 6.5 Success and Cancel Screens

What it does:
- shows clear user feedback after Stripe redirect
- success screen can refresh order status from backend

Where:
- `stripe-frontend/src/pages/CheckoutSuccessPage.js`
- `stripe-frontend/src/pages/CheckoutCancelPage.js`
- shared card: `stripe-frontend/src/components/checkout/CheckoutStatusCard.js`

## 6.6 Order Status APIs

What they do:
- fetch order by internal order id
- fetch order by Stripe checkout session id
- reconcile order with Stripe when needed

APIs:
- `GET /orders/{order_id}`
- `GET /orders/by-session/{checkout_session_id}`

Where:
- route: `backend/app/api/routes/orders.py`
- reconciliation logic: `backend/app/services/order_service.py`

## 6.7 Stripe Webhooks (Critical)

What it does:
- receives event notifications from Stripe
- verifies webhook signature (`Stripe-Signature` + `STRIPE_WEBHOOK_SECRET`)
- updates DB status based on event type

API:
- `POST /webhooks/stripe`

Where:
- route: `backend/app/api/routes/webhooks.py`
- processor: `backend/app/services/webhook_service.py`

Supported important event types:
- `checkout.session.completed`
- `checkout.session.async_payment_succeeded`
- `checkout.session.async_payment_failed`
- `checkout.session.expired`
- `payment_intent.payment_failed`

## 6.8 Idempotent Event Processing

What it does:
- ensures duplicate Stripe retries do not double-update your DB
- stores each Stripe event id once

Where:
- table: `stripe_webhook_events`
- code: `backend/app/services/webhook_service.py`

## 6.9 Database Persistence

What it does:
- stores every order lifecycle status
- stores event audit trail

Where:
- models: `backend/app/db/models.py`
- engine/session: `backend/app/db/session.py`

## 6.10 Reconciliation Fallback for `pending`

What it does:
- if webhook is missing temporarily, order API checks Stripe directly
- updates `pending` to `paid` or `expired` if Stripe confirms final state

Where:
- `backend/app/services/order_service.py`

Note:
- this is a resilience fallback, not a webhook replacement

## 6.11 PaymentIntent Endpoint (Learning Feature)

What it does:
- creates `PaymentIntent` for custom Stripe Elements style flows
- currently your main flow uses hosted Checkout, but this endpoint is available

API:
- `POST /create-payment-intent`

Where:
- route: `backend/app/api/routes/checkout.py`
- service: `backend/app/services/stripe_checkout.py`

## 7. Database Design Explained for Beginners

## 7.1 `orders` Table

Purpose:
- one row per checkout attempt/order

Key columns:
- `id`: internal UUID
- `status`: `created`, `pending`, `paid`, `payment_failed`, `expired`
- `product_name`, `unit_amount`, `quantity`, `total_amount`, `currency`
- `customer_email`, `description`
- `checkout_session_id`, `payment_intent_id`, `stripe_customer_id`
- `failure_reason`, `paid_at`, `created_at`, `updated_at`

## 7.2 `stripe_webhook_events` Table

Purpose:
- event log + idempotency guard

Key columns:
- `stripe_event_id` (unique)
- `event_type`
- `order_id`
- `payload_json`
- `processed_at`

Why this design is good:
- traceable
- retry-safe
- easier debugging/auditing

## 8. Order Status Lifecycle

Normal transitions:
- `created` -> `pending` when session is created
- `pending` -> `paid` on success
- `pending` -> `payment_failed` on failure
- `pending` -> `expired` on expiry

Rule:
- once `paid`, do not downgrade to failure

## 9. Environment Variables (What Each One Means)

Required:
- `STRIPE_SECRET_KEY`: backend credential to call Stripe APIs

Required for webhooks:
- `STRIPE_WEBHOOK_SECRET`: secret used to verify Stripe webhook signatures

Database:
- `DATABASE_URL`: PostgreSQL recommended

Frontend integration:
- `FRONTEND_BASE_URL`: used to build success/cancel redirect URLs
- `FRONTEND_ORIGINS`: CORS allowlist

Default form values:
- `DEFAULT_PRODUCT_NAME`
- `DEFAULT_AMOUNT_CENTS`
- `DEFAULT_QUANTITY`
- `DEFAULT_CURRENCY`

Safety limits:
- `MAX_AMOUNT_CENTS`
- `MAX_QUANTITY`

## 10. Local Setup and Testing

1. Install dependencies.
2. Set `.env` and `stripe-frontend/.env`.
3. Start backend:

```bash
./myenv/bin/python -m uvicorn backend.main:app --reload --port 8000
```

4. Start frontend:

```bash
cd stripe-frontend
npm start
```

5. Start webhook forwarding:

```bash
stripe listen --forward-to localhost:8000/webhooks/stripe
```

6. Copy generated `whsec_...` value into `.env` as `STRIPE_WEBHOOK_SECRET`, then restart backend.

## 11. Why Stripe Shows Success but App Shows Pending

Root cause:
- webhook not delivered or not verified, so DB status does not move from `pending`

Most common reasons:
- missing `STRIPE_WEBHOOK_SECRET`
- `stripe listen` not running locally
- wrong webhook endpoint URL

How this project handles it now:
- primary: webhook updates DB in real time
- fallback: order read APIs reconcile with Stripe and self-heal status

## 12. Common Beginner Mistakes and Fixes

1. Mistake: trusting frontend redirect as payment confirmation.
   Fix: trust webhook + DB status.
2. Mistake: forgetting webhook secret.
   Fix: set `STRIPE_WEBHOOK_SECRET` from Stripe CLI/dashboard.
3. Mistake: duplicate event side effects.
   Fix: idempotency with unique `stripe_event_id`.
4. Mistake: amount too low for currency minimum.
   Fix: obey minimum totals (for example INR >= 5000 smallest unit total).
5. Mistake: checking wrong database in DBeaver.
   Fix: verify `DATABASE_URL` currently used by backend.

## 13. API Reference Snapshot

- `GET /health`
- `GET /checkout-defaults`
- `POST /create-checkout-session`
- `POST /create-payment-intent`
- `GET /orders/{order_id}`
- `GET /orders/by-session/{checkout_session_id}`
- `POST /webhooks/stripe`

## 14. Quick Glossary (Simple Terms)

- **Payment Gateway:** service that securely processes payments between app and banks/networks.
- **Checkout Session:** Stripe object representing one hosted checkout flow.
- **PaymentIntent:** Stripe object representing a payment attempt and its state.
- **Webhook:** server-to-server event notification from Stripe.
- **Idempotency:** processing retries safely without duplicate side effects.
- **CORS:** browser security rule controlling which frontend domains can call backend APIs.

## 15. Production Checklist

- Use PostgreSQL in production.
- Keep webhook secret protected and rotate if leaked.
- Prefer migrations (Alembic) over `create_all` for schema evolution.
- Add monitoring and alerting for webhook failures.
- Keep retry-safe/idempotent event processing mandatory.

---

If you understand Sections 1, 5, 6, and 11, you understand the core of real-world payment gateway integration.
