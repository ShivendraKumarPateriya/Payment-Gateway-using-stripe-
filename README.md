# Stripe Payment Gateway (FastAPI + React)

This project is a beginner-friendly Stripe integration that now includes:

- dynamic checkout creation
- webhook signature verification
- idempotent webhook processing
- PostgreSQL-backed order/payment persistence
- order status APIs connected to frontend success page

## Full Learning Document

Read this for full end-to-end explanation (Lessons 8 and 9 + production pitfalls):

- `docs/STRIPE_PAYMENT_SYSTEM_GUIDE.md`

## Updated Backend Structure

```text
backend/
  app/
    api/routes/
      checkout.py
      orders.py
      webhooks.py
    core/config.py
    db/
      base.py
      models.py
      session.py
    schemas/checkout.py
    services/
      order_service.py
      stripe_checkout.py
      webhook_service.py
    main.py
  main.py
```

## Updated Frontend Structure

```text
stripe-frontend/src/
  components/checkout/
  config/environment.js
  pages/
  services/checkoutApi.js
  styles/checkout.css
  App.js
```

## Quick Start

1. Install backend dependencies:

```bash
./myenv/bin/pip install -r requirements.txt
```

2. Configure environment:

```bash
cp .env.example .env
cp stripe-frontend/.env.example stripe-frontend/.env
```

3. Start backend:

```bash
./myenv/bin/python -m uvicorn backend.main:app --reload --port 8000
```

4. Start frontend:

```bash
cd stripe-frontend
npm start
```

## Main API Endpoints

- `GET /health`
- `GET /checkout-defaults`
- `POST /create-checkout-session`
- `POST /create-payment-intent`
- `GET /orders/{order_id}`
- `GET /orders/by-session/{checkout_session_id}`
- `POST /webhooks/stripe`

## Important Notes

- Frontend redirect success is not the payment source of truth.
- Webhooks are the source of truth for final payment state.
- For real deployments, use PostgreSQL and set `STRIPE_WEBHOOK_SECRET`.
- If an order is still `pending`, ensure Stripe webhook forwarding/secret is configured.
- As a resilience fallback, order status endpoints now perform Stripe reconciliation for non-terminal orders.

## DBeaver: Where Are My Tables?

- If `DATABASE_URL` is **not set**, backend uses SQLite file:
  - `stripe_payments.db` in project root.
- If `DATABASE_URL` points to PostgreSQL, tables are created in that PostgreSQL database.
- Tables created by this project:
  - `orders`
  - `stripe_webhook_events`
