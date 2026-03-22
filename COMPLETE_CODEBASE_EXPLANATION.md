# Complete Stripe Payment Gateway Codebase Explanation
## For Absolute Beginners

---

## Table of Contents
1. [Fundamentals](#fundamentals)
2. [Project Architecture](#project-architecture)
3. [Folder & File Structure](#folder--file-structure)
4. [Component-by-Component Breakdown](#component-by-component-breakdown)
5. [Complete End-to-End Payment Flow](#complete-end-to-end-payment-flow)
6. [Key Concepts Explained](#key-concepts-explained)
7. [How to Run & Test](#how-to-run--test)

---

## Fundamentals

### What is a Payment Gateway?

A **payment gateway** is a secure service that handles money transactions. Think of it like an ATM for your website:

- **Without a payment gateway:** You can't safely collect credit card information
- **With a payment gateway (Stripe):** The payment gateway handles ALL the sensitive data, your app just asks for money

**In this project:**
- Your React website asks for payment
- Stripe handles the actual credit card payment
- Your backend database keeps track of the orders
- Webhooks notify your backend when payment succeeds/fails

### Key Players in This System

```
┌─────────────────┐
│   Your React    │ <- User fills form and clicks "Pay"
│    Frontend     │
└────────┬────────┘
         │ 1. Send order details
         ▼
┌─────────────────┐
│   Your FastAPI  │ <- Validates data, creates database record
│    Backend      │ <- Tells Stripe to create checkout page
└────────┬────────┘
         │ 2. Request to create Stripe session
         ▼
┌─────────────────┐
│    Stripe      │ <- Hosted checkout page
│   Servers      │ <- Handles credit card securely
└────────┬────────┘
         │ 3. User pays on Stripe page
         │ 4. Stripe notifies your backend (webhook)
         ▼
┌─────────────────┐
│   Database      │ <- Orders table updated with payment status
│   (SQLite/      │ <- Webhook events logged
│   PostgreSQL)   │
└─────────────────┘
```

### Why Stripe for Payment?

Stripe is trusted by millions because:
- **Security:** They handle credit cards (you never see them)
- **Features:** Checkout pages, subscriptions, webhook notifications
- **Easy to learn:** Great documentation and SDKs
- **Testable:** Free test mode for learning

---

## Project Architecture

### High-Level Overview

This project has **3 main layers:**

```
LAYER 1: FRONTEND (React)
├── CheckoutForm.js      → Form for user to enter payment details
├── CheckoutStartPage.js → Initial payment page
├── CheckoutSuccessPage.js → Success/confirmation page
└── checkoutApi.js       → Talks to backend

LAYER 2: BACKEND (FastAPI)
├── Routes (API endpoints)
│   ├── checkout.py      → Create payment sessions
│   ├── orders.py        → Check order status
│   └── webhooks.py      → Receive Stripe notifications
├── Services (Business Logic)
│   ├── stripe_checkout.py → Stripe API calls
│   ├── webhook_service.py → Process Stripe events
│   └── order_service.py → Check payment status from Stripe
├── Database (Data Storage)
│   ├── models.py        → Order and WebhookEvent tables
│   └── session.py       → Database connection
└── Core (Configuration)
    └── config.py        → Environment variables

LAYER 3: DATA (Database)
├── orders table         → Stores payment orders
└── stripe_webhook_events → Logs all Stripe events received
```

### Key Concepts in One Sentence Each

- **Order:** A record of something being purchased (amount, product name, customer email)
- **Checkout Session:** A Stripe-hosted page where users pay safely
- **Payment Intent:** Another way to request payment (advanced)
- **Webhook:** Stripe's way of notifying your backend "payment succeeded!"
- **Idempotent:** Can receive the same webhook 10 times, only process once
- **Reconciliation:** Checking Stripe to confirm payment status if webhook gets lost

---

## Folder & File Structure

```
Payment-Gateway-using-stripe-/
│
├── backend/                          # Python/FastAPI code
│   ├── main.py                      # Entry point (imports from app/)
│   └── app/                         # Main application package
│       ├── main.py                  # FastAPI setup & CORS
│       ├── api/
│       │   ├── __init__.py         # Exports all routers
│       │   └── routes/
│       │       ├── checkout.py     # POST /create-checkout-session
│       │       ├── orders.py       # GET /orders/{id}
│       │       └── webhooks.py     # POST /webhooks/stripe
│       ├── core/
│       │   └── config.py           # Read environment variables
│       ├── db/
│       │   ├── base.py             # SQLAlchemy setup
│       │   ├── models.py           # Order and WebhookEvent tables
│       │   ├── session.py          # Database connection functions
│       │   └── __init__.py         # Exports models & functions
│       ├── services/
│       │   ├── stripe_checkout.py  # Create Stripe sessions
│       │   ├── webhook_service.py  # Process webhook events
│       │   └── order_service.py    # Get order status from Stripe
│       └── schemas/
│           └── checkout.py         # Request/Response validation
│
├── stripe-frontend/                # React.js code
│   ├── package.json               # JavaScript dependencies
│   ├── public/
│   │   └── index.html            # HTML entry point
│   └── src/
│       ├── App.js                # Main app component
│       ├── index.js              # React entry point
│       ├── config/
│       │   └── environment.js    # Frontend configuration
│       ├── components/
│       │   └── checkout/
│       │       ├── CheckoutForm.js      # Form component
│       │       └── CheckoutStatusCard.js # Status display
│       ├── pages/
│       │   ├── CheckoutStartPage.js     # /{route}
│       │   ├── CheckoutSuccessPage.js   # /success
│       │   └── CheckoutCancelPage.js    # /cancel
│       ├── services/
│       │   └── checkoutApi.js    # Calls backend API
│       └── styles/
│           └── checkout.css      # Styling
│
├── docs/
│   └── STRIPE_PAYMENT_SYSTEM_GUIDE.md # Detailed documentation
│
├── requirements.txt               # Python dependencies
├── package.json                  # Root JavaScript package
├── README.md                     # Quick start guide
└── .env (not in git)            # Your secret keys (CREATE THIS!)
```

---

## Component-by-Component Breakdown

### 1. BACKEND: Configuration (`backend/app/core/config.py`)

**What it does:** Reads environment variables and provides settings to the whole app

**Key Settings:**
```python
STRIPE_SECRET_KEY       # Your Stripe API key (SECRET - keep safe!)
STRIPE_WEBHOOK_SECRET   # For verifying webhooks are really from Stripe
DATABASE_URL            # Where to store orders (SQLite or PostgreSQL)
FRONTEND_BASE_URL       # Where your React app is running (http://localhost:3000)
DEFAULT_PRODUCT_NAME    # "Demo Product" - prefilled if user doesn't specify
DEFAULT_AMOUNT_CENTS    # 1000 cents = $10.00
DEFAULT_CURRENCY        # "usd"
```

**Why separate config?** Makes it easy to change values without editing code. In production, these come from secure environment variables, not hardcoded.

---

### 2. BACKEND: Database Models (`backend/app/db/models.py`)

**Two main database tables:**

#### Order Table
```
orders table:
├── id (UUID)                    # Unique identifier for this order
├── status (enum)                # "created" → "pending" → "paid" (or "payment_failed")
├── product_name                 # "Demo Product"
├── unit_amount                  # Price per item in cents (e.g., 1000 = $10.00)
├── quantity                     # How many of this item (e.g., 2)
├── total_amount                 # unit_amount × quantity
├── currency                     # "usd", "eur", "gbp", etc.
├── description                  # Optional product description
├── customer_email               # User's email
├── checkout_session_id          # ID from Stripe (for linking)
├── payment_intent_id            # ID from Stripe (alternative payment method)
├── failure_reason               # If payment failed, why?
├── paid_at                      # Timestamp when payment succeeded
├── created_at                   # When order was created
└── updated_at                   # When order was last updated
```

**Status Flow:**
```
created (user just clicked checkout)
   ↓
pending (Stripe session created, user on Stripe page)
   ↓
paid (webhook says "payment_charge.succeeded")
   
OR payment_failed (webhook says payment failed)
OR expired (user walked away from Stripe page)
```

#### StripeWebhookEvent Table
```
stripe_webhook_events table:
├── id (auto-increment)          # Just a counter
├── stripe_event_id              # Stripe's unique event ID
├── event_type                   # "charge.succeeded", "charge.failed", etc.
├── order_id (foreign key)       # Link to Orders table
├── payload_json                 # Full Stripe event data (stored as backup)
├── processed_at                 # When backend received this event
└── livemode                     # Test event or real money?
```

**Why store webhook events?** 
- Prevents processing the same webhook twice (idempotency)
- Audit trail of everything Stripe told us
- Debug failed payments

---

### 3. BACKEND: API Routes

#### Route 1: Checkout (`backend/app/api/routes/checkout.py`)

**Endpoint: `POST /create-checkout-session`**

**What it does:**
1. Validates user input (amount, currency, quantity)
2. Creates an Order record in database with `status="created"`
3. Tells Stripe to create a checkout session
4. Updates Order with `status="pending"` and Stripe's session ID
5. Returns URL to Stripe's checkout page

**Frontend sends:**
```json
{
  "item": {
    "product_name": "Widget",
    "unit_amount": 1000,      // $10.00
    "quantity": 2,
    "currency": "usd",
    "description": "A blue widget"
  },
  "customer_email": "user@example.com",
  "success_path": "/success",      // Where to redirect after payment
  "cancel_path": "/cancel"         // Where to redirect if user cancels
}
```

**Backend returns:**
```json
{
  "id": "ord_12345",                          // Order ID (for tracking)
  "checkout_session_id": "cs_test_abc123",   // Stripe's session ID
  "status": "pending",
  "url": "https://checkout.stripe.com/..."   // Redirect user here!
}
```

**Flow:**
```
Frontend                Backend              Database             Stripe
   │                     │                      │                   │
   ├──POST request──────>│                      │                   │
   │                     ├──Create order───────>│                   │
   │                     │<──Order created──────┤                   │
   │                     ├──Create session──────────────────────────>│
   │                     │<──Session URL returned──────────────────<─┤
   │                     ├──Update order──────>│                   │
   │                     │<──Order updated─────┤                   │
   │<──Return URL────────┤                      │                   │
   │                     │                      │                   │
   └─Redirect to Stripe──────────────────────────────────────────────>
```

#### Route 2: Orders (`backend/app/api/routes/orders.py`)

**Endpoints:**
- `GET /orders/{order_id}` - Get order by internal ID
- `GET /orders/by-session/{session_id}` - Get order by Stripe session ID

**What it does:**
1. Retrieves order from database
2. If order status is `pending`, checks with Stripe to see if payment finished
3. Updates database if Stripe says payment succeeded
4. Returns order status to frontend

**Why?** If webhooks are slow or lost, this reconciliation ensures frontend gets real payment status.

**Returns:**
```json
{
  "id": "ord_12345",
  "status": "paid",           // OR "pending", "payment_failed", etc.
  "total_amount": 2000,
  "currency": "usd",
  "paid_at": "2024-03-22T10:15:30",
  "created_at": "2024-03-22T10:10:00"
}
```

#### Route 3: Webhooks (`backend/app/api/routes/webhooks.py`)

**Endpoint: `POST /webhooks/stripe`**

**What it does:**
1. Receives event notification from Stripe (e.g., "payment succeeded")
2. Verifies signature is really from Stripe (security-critical!)
3. Checks if we've already processed this event (idempotency)
4. Updates order status accordingly
5. Logs event to `stripe_webhook_events` table

**Stripe sends:**
```json
{
  "id": "evt_1234567890",           // Unique event ID
  "type": "charge.succeeded",       // Event type
  "data": {
    "object": {
      "id": "ch_1234567890",
      "status": "succeeded",
      "metadata": {
        "order_id": "ord_12345"
      }
    }
  }
}
```

**Important: Signature Verification**

Stripe sends a header `Stripe-Signature` that proves the request really came from Stripe:

```python
# Backend verifies this signature using STRIPE_WEBHOOK_SECRET
stripe.Webhook.construct_event(
    payload=payload_bytes,           # The request body
    sig_header=stripe_signature,     # The header from Stripe
    secret=settings.stripe_webhook_secret  # Your webhook secret
)
```

Without this verification, a hacker could fake webhook events!

---

### 4. BACKEND: Services (Business Logic)

#### Service 1: StripeCheckoutService (`backend/app/services/stripe_checkout.py`)

**Responsibility:** Handle Stripe API calls for checkout

**Main method: `create_checkout_session()`**
```python
def create_checkout_session(self, payload, db_session):
    # 1. Validate amounts aren't too small/large
    self._validate_amount(payload.item.unit_amount)
    self._validate_quantity(payload.item.quantity)
    self._validate_total_amount(...)
    
    # 2. Create local order record
    order = self._create_order_record(payload, db_session)
    
    # 3. Build success/cancel URLs
    success_url = self._build_success_url(payload.success_path)
    cancel_url = self._build_cancel_url(payload.cancel_path)
    
    # 4. Ask Stripe to create checkout session
    session = stripe.checkout.Session.create(...)
    
    # 5. Store Stripe session ID in order
    order.checkout_session_id = session.id
    order.status = "pending"
    db_session.add(order)
    db_session.commit()
    
    # 6. Return checkout URL to frontend
    return session.url
```

**Key validations:**
```python
MINIMUM_TOTAL_BY_CURRENCY = {
    "usd": 50,      # Stripe won't accept less than $0.50
    "inr": 5000,    # Less than ₹50 due to exchange rates
}
```

#### Service 2: StripeWebhookService (`backend/app/services/webhook_service.py`)

**Responsibility:** Process webhook events idempotently

**Main method: `process_event()`**
```python
def process_event(self, event, db_session):
    event_id = event["id"]
    
    # 1. Check if we already processed this event
    duplicate = db_session.query(StripeWebhookEvent)
                          .filter_by(stripe_event_id=event_id)
                          .first()
    if duplicate:
        return True, event_id  # Skip - already processed
    
    # 2. Find which order this event is about
    order = self._find_order_for_event(db_session, event)
    
    # 3. Update order status based on event type
    if event["type"] == "charge.succeeded":
        order.status = "paid"
        order.paid_at = now()
    elif event["type"] == "charge.failed":
        order.status = "payment_failed"
    
    # 4. Log this webhook event
    event_log = StripeWebhookEvent(...)
    db_session.add(event_log)
    db_session.commit()
    
    return False, event_id  # Not a duplicate
```

**Why idempotency matters:** Stripe might send the same webhook twice if it doesn't get acknowledgment. Without checking for duplicates, you'd mark an order as "paid" twice!

#### Service 3: OrderService (`backend/app/services/order_service.py`)

**Responsibility:** Fetch live payment status from Stripe as fallback

**Main method: `sync_order_from_stripe()`**

Used when:
- Frontend success page loads
- Order status is still `pending` (webhook might be late)

Does:
```python
def sync_order_from_stripe(self, order, db_session):
    # Only check if order is still pending
    if order.status != "pending":
        return order
    
    # Ask Stripe about this payment
    payment_intent = stripe.PaymentIntent.retrieve(
        order.payment_intent_id
    )
    
    # Update order based on Stripe's answer
    if payment_intent.status == "succeeded":
        order.status = "paid"
        order.paid_at = now()
    elif payment_intent.status == "requires_action":
        # Still processing
        pass
    
    db_session.add(order)
    db_session.commit()
    return order
```

**Reconciliation Feature:** This allows orders to update even if Stripe's webhook was lost!

---

### 5. FRONTEND: React Components

#### App.js (Root Component)

**What it does:**
- Routes between StartPage, SuccessPage, CancelPage
- Reads URL parameters (success URL has `?session_id=cs_123`)
- Manages page state

**Flow:**
```javascript
function App() {
  // 1. Read URL path
  if (location.pathname === "/") {
    return <CheckoutStartPage />    // Show form
  } else if (location.pathname === "/success") {
    // Extract session_id from URL: /success?session_id=cs_test_123
    return <CheckoutSuccessPage sessionId={sessionId} />  // Show status
  } else if (location.pathname === "/cancel") {
    return <CheckoutCancelPage />   // User cancelled
  }
}
```

#### Components

**CheckoutForm.js**
- Input fields for product, amount, quantity, email
- Calls `/checkout-defaults` to prefill with backend defaults
- On submit, calls `/create-checkout-session`
- Redirects user to Stripe checkout page

**CheckoutStatusCard.js**
- Shows "Payment successful!" message
- Displays order status from database
- Shows paid amount and timestamp

#### Services

**checkoutApi.js**
```javascript
// Fetch backend defaults to prefill form
async function fetchCheckoutDefaults() {
  return fetch("/checkout-defaults")
}

// Create checkout session
async function createCheckoutSession(payload) {
  return fetch("/create-checkout-session", {
    method: "POST",
    body: JSON.stringify(payload)
  })
}

// Get order status after payment
async function fetchOrderBySessionId(sessionId) {
  return fetch(`/orders/by-session/${sessionId}`)
}
```

---

## Complete End-to-End Payment Flow

### Step 1: User Opens App
```
User navigates to http://localhost:3000
   ↓
App.js renders CheckoutStartPage
   ↓
CheckoutForm fetches GET /checkout-defaults
   ↓
Backend returns: {
     product_name: "Demo Product",
     unit_amount: 1000,
     quantity: 1,
     currency: "usd"
   }
   ↓
Form is prefilled with these values
```

### Step 2: User Fills Form & Clicks "Pay"
```
User types:
  - Product: "Laptop"
  - Price: $500.00
  - Quantity: 2
  - Email: john@example.com
   ↓
Clicks "Pay" button
```

### Step 3: Frontend Sends Order to Backend
```
Frontend POSTs to /create-checkout-session:
{
  "item": {
    "product_name": "Laptop",
    "unit_amount": 50000,    // $500.00
    "quantity": 2,
    "currency": "usd"
  },
  "customer_email": "john@example.com",
  "success_path": "/success",
  "cancel_path": "/cancel"
}
   ↓
Reaches routes/checkout.py:create_checkout_session()
```

### Step 4: Backend Creates Order Record
```
route handler calls:
  service.create_checkout_session(payload, db_session)
   ↓
Service validates:
  - unit_amount > 50 USD cents? ✓
  - quantity > 0? ✓
  - total_amount (50000 * 2 = 100000) > minimum? ✓
   ↓
Service creates Order in database:
  INSERT INTO orders (
    id: "ord_abc123",
    status: "created",
    product_name: "Laptop",
    unit_amount: 50000,
    quantity: 2,
    total_amount: 100000,
    currency: "usd",
    customer_email: "john@example.com",
    created_at: now()
  )
```

### Step 5: Backend Tells Stripe to Create Checkout Session
```
Service calls:
  stripe.checkout.Session.create(
    mode="payment",
    line_items=[{
      price_data: {
        currency: "usd",
        product_data: {name: "Laptop"},
        unit_amount: 50000
      },
      quantity: 2
    }],
    success_url: "http://localhost:3000/success?session_id=cs_test_abc",
    cancel_url: "http://localhost:3000/cancel"
  )
   ↓
Stripe responds with:
  session_id: "cs_test_abc123"
  url: "https://checkout.stripe.com/pay/cs_test_abc123"
```

### Step 6: Backend Updates Order & Returns Checkout URL
```
Service updates order:
  UPDATE orders 
  SET status="pending", checkout_session_id="cs_test_abc123"
  WHERE id="ord_abc123"
   ↓
Service returns to frontend:
  {
    "id": "ord_abc123",
    "status": "pending",
    "checkout_session_id": "cs_test_abc123",
    "url": "https://checkout.stripe.com/pay/cs_test_abc123"
  }
```

### Step 7: Frontend Redirects User to Stripe
```
Frontend receives checkout URL
   ↓
JavaScript calls:
  window.location.href = "https://checkout.stripe.com/pay/..."
   ↓
User's browser navigates to Stripe's hosted checkout page
   ↓
User sees:
  - Item: "Laptop"
  - Total: $1,000.00 (50000 cents × 2)
```

### Step 8: User Pays on Stripe Page
```
User enters credit card (TEST MODE: 4242 4242 4242 4242)
   ↓
User clicks "Pay" button
   ↓
Stripe processes payment securely
   ↓
Stripe's server talks to card network/bank
   ↓
Payment succeeds!
```

### Step 9: Stripe Redirects User Back to Your App
```
Stripe has "success_url" from Step 5:
  "http://localhost:3000/success?session_id=cs_test_abc123"
   ↓
User's browser redirected there
   ↓
App.js sees URL path = "/success"
   ↓
Renders CheckoutSuccessPage with sessionId="cs_test_abc123"
```

### Step 10: Meanwhile, Stripe Sends Webhook to Backend
```
At the same time (parallel to step 9), Stripe's servers:
   ↓
POSTs to your backend at /webhooks/stripe
   ↓
Includes header: Stripe-Signature: v1=xyz...
   ↓
Includes JSON body:
  {
    "id": "evt_12345",
    "type": "charge.succeeded",
    "data": {
      "object": {
        "id": "ch_987654",
        "client_reference_id": "ord_abc123",  // Links to our order!
        "status": "succeeded",
        "amount": 100000
      }
    }
  }
```

### Step 11: Backend Verifies & Processes Webhook
```
Webhook endpoint:
  1. Verifies Stripe-Signature using STRIPE_WEBHOOK_SECRET
     ✓ Signature valid? Continue
     ✗ Signature invalid? Reject with 400

  2. Checks if this event was already processed
     (Query StripeWebhookEvent table for stripe_event_id="evt_12345")
     ✓ Already processed? Return 200 OK (idempotency)
     ✗ New event? Continue

  3. Finds the Order
     (Query: WHERE client_reference_id = "ord_abc123")
     Found: order_id = "ord_abc123"

  4. Updates order based on event type
     Since event_type = "charge.succeeded":
       UPDATE orders 
       SET status="paid", paid_at=now()
       WHERE id="ord_abc123"

  5. Logs the webhook event
     INSERT INTO stripe_webhook_events (
       stripe_event_id: "evt_12345",
       event_type: "charge.succeeded",
       order_id: "ord_abc123",
       payload_json: {...full event...}
     )

  6. Returns 200 OK to Stripe
```

### Step 12: Frontend Shows Success & Confirms with Backend
```
CheckoutSuccessPage component loads
   ↓
useEffect calls:
  fetchOrderBySessionId("cs_test_abc123")
   ↓
Calls backend: GET /orders/by-session/cs_test_abc123
   ↓
Backend route:
  1. Queries: WHERE checkout_session_id = "cs_test_abc123"
  2. Finds order_id = "ord_abc123"
  3. Order status = "paid" (updated by webhook!)
  4. Returns order data
   ↓
Frontend displays:
  "Your payment was successful"
  "Status: paid"
  "Amount: $1,000.00"
  "Date: March 22, 2024"
```

**The complete flow takes 5-10 seconds from payment to confirmation!**

---

## Key Concepts Explained

### Idempotency (Why We Track Events)

**Problem:** What if Stripe sends the same webhook twice?

```
Webhook 1 arrives: order.status = "pending" → "paid" ✓
   ↓
Network hiccup, backend doesn't acknowledge
   ↓
Webhook 2 arrives (retry): order.status = "paid" → "paid" 
   (without idempotency check: "pending" → "paid" again!)
   ↓
Result: order marked as paid twice = confusing!
```

**Solution:** Check if we've seen this event before:

```python
# Check: Does StripeWebhookEvent table have this stripe_event_id?
duplicate_event = db_session.query(StripeWebhookEvent).filter_by(
    stripe_event_id=event_id
).first()

if duplicate_event:
    # Already processed, skip
    return 200 OK
else:
    # First time seeing this, process it
    process_event()
    insert_into_stripe_webhook_events()
```

### Reconciliation (Why We Check Stripe)

**Problem:** What if the webhook gets lost?

```
Backend creates order, tells Stripe
   ↓
Stripe processes payment successfully
   ↓
Webhook sent... but network hiccup loses it!
   ↓
Frontend success page loads and asks backend: "Is it paid?"
   ↓
Backend checks database: status = "pending" (webhook never arrived!)
   ↓
Result: Frontend shows "checking..." but payment was actually successful!
```

**Solution:** If status is pending, ask Stripe directly:

```python
# In OrderService.sync_order_from_stripe():
if order.status == "pending":
    # Ask Stripe: what's the real status of this payment?
    payment_intent = stripe.PaymentIntent.retrieve(
        order.payment_intent_id
    )
    
    # Stripe says: "payment succeeded"
    if payment_intent.status == "succeeded":
        # Update order in our database
        order.status = "paid"
        
    # Database and Stripe are now in sync!
```

### Security: Webhook Signature Verification

**Problem:** How do we know webhook actually came from Stripe, not a hacker?

```
Stripe sends webhook with header:
  Stripe-Signature: v1=abc123xyz...
  
This signature is created using:
  1. Webhook payload (the JSON body)
  2. Webhook timestamp
  3. Your STRIPE_WEBHOOK_SECRET (only you and Stripe know this)
  
Hacker can't fake this because they don't know your secret!
```

**How it works:**
```python
try:
    # Backend reconstructs the signature
    event = stripe.Webhook.construct_event(
        payload=raw_body,
        sig_header=stripe_signature,
        secret=settings.stripe_webhook_secret
    )
    # If signature doesn't match, this throws an exception
except stripe.error.SignatureVerificationError:
    # Reject - not from Stripe!
    return 400 Bad Request
```

### Minimum Amount Validation

**Problem:** Stripe has minimum charges per currency:
- USD: Can't charge less than $0.50
- EUR: Can't charge less than €0.50
- INR: Can't charge less than ₹50 (due to exchange rates)

**Solution:** Validate before sending to Stripe:

```python
MINIMUM_TOTAL_BY_CURRENCY = {
    "usd": 50,      # 50 cents
    "eur": 50,      # 50 cents
    "inr": 5000,    # 5000 paise
}

# Check: total_amount >= minimum?
if total_amount < MINIMUM_TOTAL_BY_CURRENCY[currency]:
    raise ValueError("Amount too small")
```

---

## How to Run & Test

### 1. Set Up Environment

```bash
# Create .env file in project root
cat > .env << EOF
STRIPE_SECRET_KEY=sk_test_your_secret_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here
DATABASE_URL=sqlite:///./stripe_payments.db
FRONTEND_BASE_URL=http://localhost:3000
DEFAULT_AMOUNT_CENTS=1000
DEFAULT_PRODUCT_NAME=Demo Product
EOF
```

**Get Stripe keys:**
1. Go to https://dashboard.stripe.com
2. Click "Developers" → "API Keys"
3. Copy "Secret Key" (starts with `sk_`)
4. For webhook secret: go to "Webhooks" → create/view endpoint → copy secret

### 2. Start Backend

```bash
cd /home/shivendra/Payment-Gateway-using-stripe-

# Activate virtual environment
source myenv/bin/activate

# Install/update dependencies
pip install -r requirements.txt

# Start FastAPI server
python -m uvicorn backend.main:app --reload --port 8000
```

**Expected output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started server process [1234]
```

### 3. Start Frontend

```bash
cd stripe-frontend
npm install
npm start
```

**Expected output:**
```
Compiled successfully!
You can now view stripe-frontend in the browser.
Local:   http://localhost:3000
```

### 4. Test Payment Flow

```
1. Open http://localhost:3000 in browser
2. See checkout form (prefilled with defaults)
3. Click "Pay Now"
4. You're redirected to Stripe checkout
5. Enter test card: 4242 4242 4242 4242
6. Any future date (e.g., 12/26)
7. Any CVC (e.g., 123)
8. Click "Pay"
9. Redirected to success page
10. See order status: "paid"
```

### 5. Check Database

**Using SQLite (default):**
```bash
sqlite3 stripe_payments.db
> SELECT * FROM orders;
> SELECT * FROM stripe_webhook_events;
```

**Or use DBeaver GUI:**
1. Download DBeaver (free)
2. New → Database Connection → SQLite
3. Point to `stripe_payments.db`
4. Browse tables visually

---

## Debugging Common Issues

### Issue: "Missing STRIPE_SECRET_KEY"

**Fix:** You forgot to create `.env` file
```bash
cat > .env << EOF
STRIPE_SECRET_KEY=sk_test_...
EOF
```

### Issue: Frontend shows "Could not connect to backend"

**Fix:** Backend isn't running
```bash
# Terminal 1:
python -m uvicorn backend.main:app --reload --port 8000

# Terminal 2:
cd stripe-frontend && npm start
```

### Issue: Webhook not processing (order stays "pending")

**Cause:** `STRIPE_WEBHOOK_SECRET` not set

**Fix:** Add webhook secret to `.env`
```bash
STRIPE_WEBHOOK_SECRET=whsec_your_secret...
```

**To test webhook locally:**
```bash
# Install Stripe CLI
# https://stripe.com/docs/stripe-cli

# Login to Stripe
stripe login

# Forward webhooks to local backend
stripe listen --forward-to localhost:8000/webhooks/stripe

# Trigger test event
stripe trigger charge.succeeded
```

### Issue: "Amount too small" error

**Cause:** Entered amount less than Stripe minimum

**Fix:** For USD, enter at least $0.50

---

## Summary

### You Now Understand:

✅ What Stripe does (secure payment handling)
✅ How your 3 layers work (Frontend → Backend → Database)
✅ The complete payment flow from start to finish
✅ Why webhooks are important (source of truth)
✅ Why idempotency matters (prevent double-processing)
✅ Why reconciliation helps (recover from lost webhooks)
✅ How security works (signature verification)
✅ How to run the entire system

### Next Steps:

1. **Run the app locally** - Follow "How to Run & Test"
2. **Make test payments** - Use Stripe test cards
3. **Check database** - See orders being created and updated
4. **Modify the code** - Try changing product name, amount, etc.
5. **Deploy to production** - Use real Stripe keys and PostgreSQL

---

## Additional Resources

- **Stripe Documentation:** https://stripe.com/docs
- **FastAPI Documentation:** https://fastapi.tiangolo.com
- **React Documentation:** https://react.dev
- **SQLAlchemy Documentation:** https://docs.sqlalchemy.org

---

**Congratulations! You now understand a complete, production-ready payment gateway system.** 🎉
