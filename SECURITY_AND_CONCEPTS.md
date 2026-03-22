# Security & Key Concepts Deep Dive

## Why Security Matters in Payment Systems

You're dealing with:
- Credit card information (handled by Stripe, not you - good!)
- Customer money (real or test)
- Audit trails (who paid what, when)
- Compliance requirements (PCI-DSS, GDPR, etc.)

One security mistake = customer loses money = legal liability = you pay for it.

---

## Security Layer 1: Webhook Signature Verification

### The Problem

```
Internet:
  ├── Your Server
  ├── Stripe Servers
  └── Hacker's Computer

Hacker thinks: "I can fake a webhook and make it look like payment succeeded!"
```

### The Solution: HMAC Signature

Stripe uses **HMAC-SHA256** to prove authenticity:

```python
# How Stripe creates the signature:
timestamp = "1710843330"
body = '{"id":"evt_123","type":"charge.succeeded",...}'
secret = "[YOUR_WEBHOOK_SECRET]"

# Stripe does:
signature = HMAC_SHA256(
    message = f"{timestamp}.{body}",
    secret = secret
)

# Stripe sends:
Stripe-Signature: t=1710843330,v1=signature_value...
```

```python
# How your backend verifies:
received_signature = "signature_value..."
received_timestamp = "1710843330"

# You do:
reconstructed_signature = HMAC_SHA256(
    message = f"{received_timestamp}.{received_body}",
    secret = your_webhook_secret
)

# Check if they match:
if reconstructed_signature == received_signature:
    ✅ Signature valid - webhook is from Stripe!
else:
    ❌ Signature invalid - REJECT webhook!
```

### In Your Code

```python
# backend/app/api/routes/webhooks.py
try:
    event = stripe.Webhook.construct_event(
        payload=payload_bytes,
        sig_header=stripe_signature,
        secret=settings.stripe_webhook_secret
    )
except stripe.error.SignatureVerificationError as error:
    raise HTTPException(status_code=400, detail="Invalid signature")
```

### What Happens If You Skip This

Hacker crafts fake webhook, your backend processes it without verifying. Order marked "paid" even though customer never paid. You lose money!

---

## Security Layer 2: Idempotent Webhook Processing

### The Problem

```
Timeline:
T=0s:   Stripe sends webhook (charge.succeeded)
T=0.1s: Your backend processes it → UPDATE orders SET status='paid'
T=0.2s: Backend sends HTTP 200
T=0.5s: Network issue! Response doesn't reach Stripe
T=1s:   Stripe doesn't see 200 confirmation
T=1.5s: Stripe retries webhook (same event ID!)
T=1.6s: Your backend processes it AGAIN
        UPDATE orders SET status='paid' (redundant!)

Result: Order marked "paid" twice = accounting confusion!
```

### The Solution: Prevent Duplicate Processing

```python
# backend/app/services/webhook_service.py
def process_event(self, event, db_session):
    event_id = event["id"]
    
    # Check: Have we seen this event before?
    duplicate_event = db_session.query(StripeWebhookEvent).filter_by(
        stripe_event_id = event_id
    ).first()
    
    if duplicate_event is not None:
        # Already processed! Skip everything
        return True, event_id
    
    # First time! Process normally
    order = self._find_order_for_event(db_session, event)
    self._apply_order_updates(order, event)
    
    # Log that we processed this
    event_log = StripeWebhookEvent(
        stripe_event_id = event_id,
        event_type = event["type"],
        ...
    )
    db_session.add(event_log)
    db_session.commit()
    
    return False, event_id
```

### Database Protection

```python
# backend/app/db/models.py
stripe_event_id: Mapped[str] = mapped_column(
    String(255),
    unique=True,  # ← Only one event with this ID!
    index=True
)
```

The `unique=True` constraint means:
- First insert with id='evt_123': ✅ Success
- Second insert with id='evt_123': ❌ Constraint violation!

---

## Security Layer 3: Reconciliation (Fallback Verification)

### The Problem

```
Best case:  Webhook arrives quickly, order marked "paid"
Bad case:   Webhook is slow or lost entirely!

Result: Database shows pending but Stripe shows paid!
        You and Stripe are out of sync ❌
```

### The Solution: Ask Stripe Directly

```python
# backend/app/services/order_service.py
def sync_order_from_stripe(self, order, db_session):
    # Only reconcile if status is uncertain
    if order.status != "pending":
        return order
    
    # Ask Stripe: "What happened to this payment?"
    try:
        payment_intent = stripe.PaymentIntent.retrieve(
            order.payment_intent_id
        )
    except stripe.StripeError:
        return order
    
    # Stripe told us the real status
    if payment_intent.status == "succeeded":
        order.status = "paid"
        order.paid_at = datetime.now(timezone.utc)
        db_session.add(order)
        db_session.commit()
    
    return order
```

**Timeline with Reconciliation:**
```
T=0s:  Payment succeeds on Stripe
T=1s:  Webhook server down...
T=5s:  User refreshes success page
T=6s:  Backend checks DB: status='pending'
       Asks Stripe: "What's the real status?"
T=7s:  Stripe responds: "succeeded"
       UPDATE order: status='paid'
T=8s:  Frontend shows: "Payment successful!" ✅
```

---

## Security Layer 4: Environment Variables (Secrets)

### The Problem

```python
# ❌ INSECURE - Never do this!
stripe.api_key = "[ACTUAL_STRIPE_KEY_HERE]"

# If you commit this to GitHub, hackers can:
# - Charge customers without authorization
# - Refund their own purchases
# - Ruin your business
```

### The Solution: Environment Variables

```bash
# ✅ Create .env file (DON'T commit to git!)
cat > .env << EOF
STRIPE_SECRET_KEY=[YOUR_STRIPE_KEY]
STRIPE_WEBHOOK_SECRET=[YOUR_WEBHOOK_SECRET]
DATABASE_URL=postgresql://user:password@localhost/db
EOF

# Add to .gitignore
echo ".env" >> .gitignore
```

```python
# backend/app/core/config.py
import os
from dotenv import load_dotenv

load_dotenv()
stripe_secret_key = os.getenv("STRIPE_SECRET_KEY")

if not stripe_secret_key:
    raise RuntimeError("STRIPE_SECRET_KEY not found")
```

### For Production

```bash
# AWS Secrets Manager
export STRIPE_SECRET_KEY=$(aws secretsmanager get-secret-value \
  --secret-id stripe-key --query SecretString --output text)

# Heroku
heroku config:set STRIPE_SECRET_KEY=[YOUR_PRODUCTION_KEY]

# Docker/Kubernetes
kubectl create secret generic stripe-secrets \
  --from-literal=stripe-secret-key=[YOUR_KEY]
```

---

## Security Layer 5: HTTPS (TLS/SSL)

### Why HTTP is Insecure

```
Hacker on Coffee Shop WiFi:
  ├── Customer sends card via HTTP (no encryption)
  │   Hacker eavesdrops: card number visible ❌
  │
  └── Customer sends card via HTTPS (encrypted)
      Hacker sees: "🔒🔒🔒" (encrypted, unreadable) ✅
```

### HTTPS Prevents

1. **Interception** - Hacker can't read data in transit
2. **Tampering** - Hacker can't modify requests
3. **Spoofing** - Hacker can't pretend to be your server
4. **PCI-DSS** - Required by payment card regulations

### Force HTTPS in Production

```python
# backend/app/main.py
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

app.add_middleware(HTTPSRedirectMiddleware)
# Redirects http://mysite.com → https://mysite.com
```

---

## Security Checklist for Production

- [ ] **Webhook Signature Verification**: `stripe.Webhook.construct_event(..., secret=secret)`
- [ ] **Idempotent Webhook Processing**: Check if event already processed before updating
- [ ] **Reconciliation Fallback**: If order pending, ask Stripe for real status
- [ ] **Secrets in Environment Variables**: Never hardcode credentials
- [ ] **HTTPS Only**: Force TLS/SSL in production
- [ ] **CORS Restricted**: `allow_origins=["https://mysite.com"]` (not "*")
- [ ] **Input Validation**: Use Pydantic to validate all inputs
- [ ] **Rate Limiting**: Limit API calls per IP to prevent abuse
- [ ] **Logging**: Log events, NOT sensitive data
- [ ] **Database Backups**: Regular backups, encrypted storage

---

## Common Security Mistakes (Don't Make These!)

### Mistake 1: Trusting Frontend Validation Only

```python
# ❌ INSECURE
let amount = params.get("amount");  // User can change this!
// Attacker changes URL: ?amount=1 instead of 1000
// Gets charged $0.01 instead of $10

# ✅ SECURE
@router.post("/create-checkout-session")
def checkout(payload, ...):
    amount = payload.item.unit_amount  # Only trust POST body
    if amount < 50:  # Minimum
        raise ValueError("Amount too small")
    if amount > 999999999:  # Maximum
        raise ValueError("Amount too large")
```

### Mistake 2: Storing Credit Cards

```python
# ❌ INSECURE
order.credit_card = "4242424242424242"
# Violates PCI-DSS
# You're liable if hacked

# ✅ SECURE
order.stripe_payment_id = session.payment_intent  # Just ID, not card!
# Stripe handles the card securely
```

### Mistake 3: Logging Sensitive Data

```python
# ❌ INSECURE
logger.info(f"Webhook: {event.to_dict()}")
# Logs contain customer email, amounts, card info!

# ✅ SECURE
logger.info(f"Webhook processed: event_id={event.id}, type={event.type}")
# Only non-sensitive fields
```

### Mistake 4: Accepting Any CORS Origin

```python
# ❌ INSECURE
allow_origins=["*"]  # ANYONE can call your API!
# Attacker's website can create orders on your behalf

# ✅ SECURE
allow_origins=["https://mysite.com"]  # Only YOUR site
```

### Mistake 5: No Rate Limiting

```python
# ❌ INSECURE
@router.post("/create-checkout-session")
def checkout(...):
    # Attacker can spam 10,000 requests/second
    # Creates 10,000 orders, database crashes

# ✅ SECURE
@limiter.limit("10/minute")
def checkout(...):
    # Max 10 orders per minute per IP
    # Service stays healthy
```

---

## Testing Security

### Test Signature Verification

```bash
# 1. Start webhook listener
stripe listen --forward-to localhost:8000/webhooks/stripe

# 2. Copy webhook secret to .env
# STRIPE_WEBHOOK_SECRET=[your_webhook_secret_for_testing]

# 3. Trigger test event
stripe trigger charge.succeeded

# 4. Check backend logs
# Backend should show: "Webhook processed: evt_123"
```

### Test Idempotency

```bash
# Trigger same event twice
stripe trigger charge.succeeded --override metadata_test=1
stripe trigger charge.succeeded --override metadata_test=1

# Check database:
SELECT COUNT(*) FROM stripe_webhook_events 
WHERE stripe_event_id='evt_123';

# Should show: 1 (not 2!)

# Check orders table:
SELECT status FROM orders WHERE id='ord_123';
# Should show: "paid" (not duplicated)
```

---

## Key Concepts Explained

### What is Idempotency?

Idempotency means an operation produces the same result whether executed once or multiple times.

**Example:**
```
Payment webhook (evt_123) arrives twice:

Without idempotency:
  First webhook: order.status = "pending" → "paid"
  Second webhook: order.status = "paid" → "paid" (again!)
  Database state: confused, might double-count revenue

With idempotency:
  First webhook: process, save event ID
  Second webhook: see evt_123 in database, skip processing
  Database state: "paid" (only once) ✅
```

### What is Reconciliation?

Reconciliation means comparing your data with Stripe's to make sure they agree.

**Example:**
```
Scenario: Webhook lost in network

Without reconciliation:
  User's view: "Order pending" (webhook never arrived)
  Stripe's view: "Payment succeeded" 
  Result: User confused, you don't know if paid

With reconciliation:
  User's view: "Order pending"
  Backend checks: "Ask Stripe..."
  Stripe says: "Payment succeeded"
  Updated view: "Order paid" ✅
```

### What is a Webhook?

A webhook is Stripe's way of notifying your backend when something happens.

**Timeline:**
```
T=0s:  User pays on Stripe
T=1s:  Payment succeeds
T=2s:  Stripe POST /webhooks/stripe {event: charge.succeeded}
T=3s:  Your backend receives webhook
T=4s:  Backend verifies signature (is this really from Stripe?)
T=5s:  Backend processes event, updates order status
T=6s:  Backend returns 200 OK to Stripe
T=7s:  Stripe marks event as delivered
```

---

## Key Takeaways

```
🔒 Security in Payment Systems = No Customer Money Stolen

Three Layers of Protection:
1. Stripe handles cards (you never see them)
2. Your backend verifies webhooks (signature check)
3. Your database prevents duplicates (idempotent processing)

Remember:
- Secrets go in .env, NOT in code
- Always validate on backend, not just frontend
- Never store credit card numbers
- Use HTTPS in production
- Log events, NOT sensitive data
- Restrict CORS origins
- Rate limit API endpoints

If ANY of this fails, customers lose money and you pay for it!
```

---

## Production Deployment Checklist

**Before going live with real Stripe keys:**

1. [ ] Switch database from SQLite to PostgreSQL
2. [ ] All credentials in environment variables (not code)
3. [ ] HTTPS/TLS verified and enabled
4. [ ] CORS origins restricted to your domain
5. [ ] Rate limiting enabled on all endpoints
6. [ ] Webhook secret configured from production endpoint
7. [ ] Database backups automated
8. [ ] Error logging configured (Sentry/Rollbar)
9. [ ] Performance monitoring active
10. [ ] Security scanning enabled (OWASP scanning)

---

## Further Reading

- [Stripe Security Guide](https://stripe.com/docs/security)
- [PCI-DSS Compliance](https://www.pcisecuritystandards.org/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security Documentation](https://fastapi.tiangolo.com/tutorial/security/)
- [Webhook Best Practices](https://docs.svix.com/guides/webhooks/secure-webhooks)

---

**Your payment system is now secure architecture!** 🛡️
