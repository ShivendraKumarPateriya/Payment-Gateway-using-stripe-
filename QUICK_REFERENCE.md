# Quick Reference Guide - Code to Concept Mapping

## The 3-Second Elevator Pitch

You're building an e-commerce payment system:
1. **React frontend** shows a checkout form
2. **FastAPI backend** validates orders and talks to Stripe
3. **Stripe** securely handles credit cards
4. **Database** records everything for audit trail

---

## File-to-Function Quick Mapping

| What You Want to Do | Where to Find It | What Happens |
|---|---|---|
| **User fills checkout form** | `stripe-frontend/src/components/checkout/CheckoutForm.js` | Form collects product, amount, email |
| **Form validation** | `stripe-frontend/src/App.js` | Checks amount isn't too small/large |
| **Send payment request** | `stripe-frontend/src/services/checkoutApi.js` | `POST /create-checkout-session` |
| **Create Stripe session** | `backend/app/services/stripe_checkout.py` | Validates, creates order record, calls Stripe API |
| **Store order in DB** | `backend/app/db/models.py` | `Order` table gets new row |
| **Return checkout URL** | `backend/app/api/routes/checkout.py` | Frontend redirects user to Stripe page |
| **User pays on Stripe** | https://checkout.stripe.com | Stripe handles card securely |
| **Stripe notifies backend** | `backend/app/api/routes/webhooks.py` | Webhook received at `POST /webhooks/stripe` |
| **Verify webhook** | `backend/app/core/config.py` | Check `Stripe-Signature` header |
| **Process webhook** | `backend/app/services/webhook_service.py` | Find order, update status to "paid" |
| **Log webhook event** | `backend/app/db/models.py` | `StripeWebhookEvent` table gets entry |
| **Show success page** | `stripe-frontend/src/pages/CheckoutSuccessPage.js` | Call `GET /orders/by-session/{session_id}` |
| **Check order status** | `backend/app/api/routes/orders.py` | Query database, maybe reconcile with Stripe |
| **Sync with Stripe** | `backend/app/services/order_service.py` | If webhook was late, ask Stripe for real status |

---

## Key Files at a Glance

### Backend Configuration
```
backend/app/core/config.py
├── STRIPE_SECRET_KEY           ← Your Stripe API key
├── STRIPE_WEBHOOK_SECRET       ← For verifying webhooks
├── DATABASE_URL                ← Where orders are stored
├── FRONTEND_BASE_URL           ← Where frontend is running
└── DEFAULT_* settings          ← Prefill form defaults
```

### Database Schema
```
orders table:
├── id (primary key)            ← Unique order ID
├── status                      ← "created" → "pending" → "paid"
├── product_name, unit_amount   ← What's being sold
├── total_amount, currency      ← How much, in what currency
├── checkout_session_id         ← Stripe's session ID
├── created_at, updated_at      ← Timestamps
└── paid_at                     ← When payment succeeded

stripe_webhook_events table:
├── stripe_event_id             ← Stripe's unique event ID
├── event_type                  ← "charge.succeeded", etc.
├── order_id (foreign key)      ← Links to Orders table
└── payload_json                ← Full Stripe event data
```

### API Endpoints
```
GET  /health
  ↓ Returns {"status": "ok"}

GET  /checkout-defaults
  ↓ Returns prefill values

POST /create-checkout-session
  ↓ Creates order, returns Stripe checkout URL

GET  /orders/{order_id}
  ↓ Get order by internal ID

GET  /orders/by-session/{session_id}
  ↓ Get order by Stripe session ID

POST /webhooks/stripe
  ↓ Stripe calls this on payment events
```

---

## The 7-Step Payment Dance

```
Step 1:  Frontend → Backend  | "Create checkout for $100 laptop"
         ↓
Step 2:  Backend → Database   | INSERT order (status="created")
         ↓
Step 3:  Backend → Stripe     | "Create checkout session"
         ↓
Step 4:  Stripe → Backend     | "Here's session ID cs_abc123"
         ↓
Step 5:  Backend → Database   | UPDATE order (status="pending", session_id="cs_abc123")
         ↓
Step 6:  Backend → Frontend   | "Redirect to https://checkout.stripe.com/..."
         ↓
Step 7:  User → Stripe Page   | User enters card, clicks Pay
         ↓
Step 8:  Stripe → Backend     | (webhook) "charge.succeeded"
         ↓
Step 9:  Backend → Database   | UPDATE order (status="paid")
         ↓
Step 10: Frontend → Backend   | "What's the order status?"
         ↓
Step 11: Backend → Frontend   | {"status": "paid"}
         ↓
Step 12: Frontend → User      | "Payment successful!"
```

---

## Status Flow Diagram

```
Order creation:
    created
       ↓ (Stripe session created)
    pending
       ↓ (Stripe webhook: "charge.succeeded")
    paid ← NORMAL PATH
    
OR (if payment fails):
       ↓ (Stripe webhook: "charge.failed")
    payment_failed
    
OR (if user abandons):
       ↓ (Stripe timeout)
    expired
```

---

## Common Error Messages & Fixes

```
Error: "STRIPE_SECRET_KEY is not configured"
Fix:   Create .env with STRIPE_SECRET_KEY=sk_test_...

Error: "Amount too small"
Fix:   Amount must be >= $0.50 for USD, etc.

Error: "Invalid webhook signature"
Fix:   STRIPE_WEBHOOK_SECRET doesn't match, regenerate webhook endpoint

Error: "Order not found"
Fix:   Order ID or session ID doesn't exist in database

Error: "Could not connect to backend"
Fix:   Backend isn't running, start it with: 
       python -m uvicorn backend.main:app --reload --port 8000

Error: "Webhook not processing, order stays pending"
Fix:   STRIPE_WEBHOOK_SECRET not set, or webhook not forwarded to /webhooks/stripe
```

---

## Test Stripe Card Numbers

```
✅ Successful payment:     4242 4242 4242 4242
❌ Declined:              4000 0000 0000 0002
⚠️  Requires 3D Secure:   4000 0000 0000 0010
🏦 International:         4000 0000 0000 0069
```

Any future expiration date, any CVC (e.g., 123)

---

## Environment Variables Explained

```env
# Stripe API Keys (from https://dashboard.stripe.com/developers)
STRIPE_SECRET_KEY=sk_test_4eC39HqLyjWDarhtT657KR...
STRIPE_WEBHOOK_SECRET=whsec_test_secret_...

# Database (SQLite default, PostgreSQL for production)
DATABASE_URL=sqlite:///./stripe_payments.db
# OR for PostgreSQL:
# DATABASE_URL=postgresql://user:password@localhost/stripe_db

# Frontend (where your React app runs)
FRONTEND_BASE_URL=http://localhost:3000
FRONTEND_ORIGINS=http://localhost:3000,http://example.com

# Defaults for form prefilling
DEFAULT_PRODUCT_NAME=Demo Product
DEFAULT_AMOUNT_CENTS=1000              # $10.00
DEFAULT_QUANTITY=1
DEFAULT_CURRENCY=usd

# Max amounts for validation
MAX_AMOUNT_CENTS=999999999
MAX_QUANTITY=1000
```

---

## Dependencies Explained

### Backend (Python)
```
fastapi            → Web framework (like Express for JavaScript)
uvicorn            → Server to run FastAPI
sqlalchemy         → Database ORM (interact with DB like objects)
psycopg            → PostgreSQL driver (if using Postgres)
python-dotenv      → Load .env files
stripe             → Stripe API client library
pydantic           → Data validation
```

### Frontend (JavaScript/React)
```
react              → Create interactive UI
react-router-dom   → Navigation between pages
```

---

## How to Debug Payment Issues

### Check if Order Exists in Database
```bash
sqlite3 stripe_payments.db
> SELECT * FROM orders WHERE id='ord_abc123';
```

### Check if Webhook Was Received
```bash
sqlite3 stripe_payments.db
> SELECT * FROM stripe_webhook_events WHERE order_id='ord_abc123';
```

### Check Webhook Signature Manually
```python
# In backend code:
print(f"Webhook secret: {settings.stripe_webhook_secret}")
print(f"Event ID: {event['id']}")
print(f"Signature: {stripe_signature}")

# Check Stripe Dashboard → Webhooks → Event details
```

### Simulate Webhook Locally
```bash
stripe listen --forward-to localhost:8000/webhooks/stripe
stripe trigger charge.succeeded --override client_reference_id=ord_abc123
```

---

## Security Checklist

- [ ] `STRIPE_SECRET_KEY` starts with `sk_` and is in `.env` (not git)
- [ ] `STRIPE_WEBHOOK_SECRET` starts with `whsec_` and is in `.env`
- [ ] Webhook signature verification is enabled in code
- [ ] Idempotency check (don't process same webhook twice)
- [ ] CORS origins are restricted to your domain
- [ ] Database is PostgreSQL in production (not SQLite)
- [ ] HTTPS is used in production (not HTTP)
- [ ] Sensitive data logged to webhook_events table
- [ ] Rate limiting enabled on API endpoints

---

## Before Going to Production

1. **Switch to PostgreSQL**
   ```bash
   DATABASE_URL=postgresql://user:pass@localhost/stripe_db
   ```

2. **Use real Stripe keys** (not test keys)
   ```bash
   STRIPE_SECRET_KEY=sk_live_4eC39HqLyjWDarhtT657...  # Real money!
   ```

3. **Set webhook secret from live endpoint**
   ```bash
   STRIPE_WEBHOOK_SECRET=whsec_live_...
   ```

4. **Deploy backend & frontend**
   - Backend: Heroku, AWS, DigitalOcean, etc.
   - Frontend: Vercel, Netlify, AWS, etc.

5. **Update FRONTEND_BASE_URL to production domain**
   ```bash
   FRONTEND_BASE_URL=https://myapp.com
   FRONTEND_ORIGINS=https://myapp.com
   ```

6. **Point Stripe webhook to production URL**
   - Stripe Dashboard → Webhooks
   - Change endpoint URL to: `https://myapp.com/api/webhooks/stripe`

7. **Backup database** (PostgreSQL has better backup tools)

8. **Monitor Stripe events** (Stripe Dashboard → Events)

9. **Enable error logging** (Sentry, LogRocket, etc.)

10. **Load test** before launch

---

## Remember These Core Concepts!

| Concept | Why It Matters | Example |
|---------|----------------|---------|
| **Idempotency** | Same webhook received twice shouldn't double-charge | If webhook arrives twice, order marked "paid" only once |
| **Reconciliation** | Webhooks might get lost | If backend unsure of status, ask Stripe directly |
| **Signature Verification** | Prove webhook is really from Stripe | Check `Stripe-Signature` header before processing |
| **Status Flow** | Order goes through predictable states | `created` → `pending` → `paid` |
| **Foreign Keys** | Link webhook events to orders | `stripe_webhook_events.order_id` → `orders.id` |
| **Amounts in Cents** | Stripe uses smallest currency unit | $10.00 = 1000 cents |
| **Success vs Cancel URLs** | Control where user goes after Stripe | Success: `/success?session_id=...`, Cancel: `/cancel` |
| **Timestamp Precision** | Know exactly when things happened | `created_at`, `updated_at`, `paid_at` store exact times |

---

**Now you can explain this entire system to anyone!** 🎓
