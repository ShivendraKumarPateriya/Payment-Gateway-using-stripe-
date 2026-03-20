# Stripe Checkout Demo (Structured Version)

This project is a beginner-friendly Stripe payment demo with a **FastAPI backend** and **React frontend**.

## What Changed

- Removed hardcoded checkout amount/product values from code.
- Backend now accepts checkout data sent from frontend form.
- Added backend defaults from environment variables.
- Refactored code into a clean folder structure with service layer and schemas.
- Added docstrings/JSDoc comments for easier learning and maintenance.

## Project Structure

```text
backend/
  app/
    api/routes/checkout.py       # HTTP endpoints
    core/config.py               # Environment settings
    schemas/checkout.py          # Request/response validation models
    services/stripe_checkout.py  # Stripe business logic
    main.py                      # App creation
  main.py                        # Compatibility entrypoint (backend.main:app)

stripe-frontend/src/
  components/checkout/           # Reusable UI pieces
  config/environment.js          # Frontend env config
  pages/                         # Start/success/cancel views
  services/checkoutApi.js        # API helper functions
  styles/checkout.css            # Page styling
  App.js                         # Main controller
```

## Environment Setup

1. Copy `.env.example` to `.env` and fill `STRIPE_SECRET_KEY`.
2. Copy `stripe-frontend/.env.example` to `stripe-frontend/.env`.

## Run Backend

```bash
./myenv/bin/python -m uvicorn backend.main:app --reload --port 8000
```

## Run Frontend

```bash
cd stripe-frontend
npm start
```

## API Endpoints

- `GET /health`: backend health check
- `GET /checkout-defaults`: default form values from backend settings
- `POST /create-checkout-session`: create Stripe Checkout session from frontend payload
- `POST /create-payment-intent`: create PaymentIntent for custom card flows

## Example Checkout Payload

```json
{
  "item": {
    "product_name": "Starter Plan",
    "unit_amount": 2500,
    "quantity": 2,
    "currency": "usd",
    "description": "One-time setup payment"
  },
  "customer_email": "customer@example.com",
  "success_path": "/success",
  "cancel_path": "/cancel",
  "allow_promotion_codes": true
}
```
