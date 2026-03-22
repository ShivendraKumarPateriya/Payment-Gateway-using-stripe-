# Code Flow Walkthrough - See Exactly What Happens

## When User Clicks "Pay Now" - Full Code Trace

### STEP 1: Frontend Form Submission

**File:** `stripe-frontend/src/components/checkout/CheckoutForm.js`
```javascript
const handleCheckoutSubmit = async (formData) => {
  // formData = {
  //   productName: "Laptop",
  //   unitAmount: 50000,    // $500 in cents
  //   quantity: 2,
  //   customerEmail: "john@example.com",
  //   ...
  // }

  // Step 1: Validate that all fields are filled
  if (!formData.productName) {
    setError("Product name is required");
    return;
  }

  // Step 2: Call API to create checkout session
  try {
    const response = await createCheckoutSession({
      item: {
        product_name: formData.productName,
        unit_amount: formData.unitAmount,
        quantity: formData.quantity,
        currency: formData.currency,
        description: formData.description,
      },
      customer_email: formData.customerEmail,
      success_path: "/success",      // Where to go after payment
      cancel_path: "/cancel",        // Where to go if user cancels
      allow_promotion_codes: true,
    });

    // Step 3: Stripe returns a checkout URL
    const { url } = response;

    // Step 4: Redirect browser to Stripe's checkout page
    window.location.href = url;

  } catch (error) {
    setError(error.message);
  }
};
```

### STEP 2: Frontend Calls Backend API

**File:** `stripe-frontend/src/services/checkoutApi.js`
```javascript
export async function createCheckoutSession(payload) {
  // This function sends the payment request to backend
  
  const response = await fetchWithTimeout(
    `${API_BASE_URL}/create-checkout-session`,  // Points to backend
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)  // Send order details
    }
  );

  // Parse response and throw error if failed
  return parseJsonResponse(response);
}

// Example: 
// Sends: POST http://localhost:8000/create-checkout-session
// With body: {
//   "item": {...},
//   "customer_email": "john@example.com",
//   "success_path": "/success"
// }
```

### STEP 3: Backend Route Receives Request

**File:** `backend/app/api/routes/checkout.py`
```python
@router.post("/create-checkout-session", response_model=CheckoutSessionResponse)
def create_checkout_session(
    payload: CheckoutSessionCreateRequest | None = Body(default=None),
    settings: AppSettings = Depends(get_settings),
    db_session: Session = Depends(get_db_session),
) -> CheckoutSessionResponse:
    """
    This function runs when frontend POSTs /create-checkout-session
    
    Parameters:
    - payload: The JSON data from frontend (validated by Pydantic)
    - settings: Configuration (from .env)
    - db_session: Database connection (SQLAlchemy)
    """

    # Step 1: Use defaults if frontend didn't send data
    checkout_payload = payload or _default_checkout_request(settings)
    
    # Step 2: Create service object to handle Stripe API calls
    service = StripeCheckoutService(settings)  # Passes STRIPE_SECRET_KEY

    # Step 3: Call service, which will:
    # - Validate amounts
    # - Create order in database
    # - Call Stripe API
    # - Update order with session ID
    try:
        return service.create_checkout_session(checkout_payload, db_session)
    except stripe.StripeError as error:
        db_session.rollback()  # Undo changes if error
        raise HTTPException(status_code=502, detail=error.user_message)
```

### STEP 4: Service Creates Order Record in Database

**File:** `backend/app/services/stripe_checkout.py`
```python
def create_checkout_session(
    self, payload: CheckoutSessionCreateRequest, db_session: Session
) -> CheckoutSessionResponse:
    """
    This method:
    1. Validates the order
    2. Creates Order row in database
    3. Calls Stripe API
    4. Updates Order with Stripe session ID
    """

    # ===== VALIDATION PHASE =====
    # Check: Is amount too small for this currency?
    self._validate_amount(payload.item.unit_amount)
    # If unit_amount < 50 cents for USD, raises ValueError
    
    # Check: Is quantity valid?
    self._validate_quantity(payload.item.quantity)
    
    # Check: Is total amount within Stripe's limits?
    self._validate_total_amount(
        amount=payload.item.unit_amount,
        quantity=payload.item.quantity,
        currency=payload.item.currency,
    )

    # ===== DATABASE PHASE =====
    # Create Order record
    order = self._create_order_record(payload, db_session)
    # This INSERT into orders table:
    # INSERT INTO orders (
    #   id,                   ← UUID (e.g., 'ord_abc123')
    #   status,               ← 'created'
    #   product_name,         ← 'Laptop'
    #   unit_amount,          ← 50000
    #   quantity,             ← 2
    #   total_amount,         ← 100000
    #   currency,             ← 'usd'
    #   customer_email,       ← 'john@example.com'
    #   created_at,           ← current timestamp
    #   updated_at            ← current timestamp
    # ) VALUES (...)

    # ===== STRIPE API PHASE =====
    # Build URLs user will be redirected to
    success_url = self._build_success_url(payload.success_path)
    # Returns: "http://localhost:3000/success?session_id=cs_test_abc123"
    
    cancel_url = self._build_cancel_url(payload.cancel_path)
    # Returns: "http://localhost:3000/cancel"

    # Call Stripe API to create checkout session
    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            
            # What's being sold
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": "Laptop",
                        "description": "High performance laptop"
                    },
                    "unit_amount": 50000,  # $500
                },
                "quantity": 2,
            }],
            
            # User's email
            customer_email="john@example.com",
            
            # Link this checkout session to our order ID
            # Stripe will return this in webhook!
            client_reference_id=order.id,
            
            # Metadata for webhook
            metadata={
                "order_id": order.id,
                "product_name": "Laptop"
            },
            
            # Where to take user after payment
            success_url=success_url,
            cancel_url=cancel_url,
        )
        # Stripe returns:
        # {
        #   "id": "cs_test_abc123",
        #   "url": "https://checkout.stripe.com/pay/cs_test_abc123",
        #   "payment_intent": "pi_test_xyz789",
        #   ...
        # }
        
    except stripe.StripeError as error:
        # If Stripe call fails, mark order as failed
        order.status = "payment_failed"
        order.failure_reason = str(error)
        db_session.add(order)
        db_session.commit()
        raise

    # ===== UPDATE ORDER WITH STRIPE INFO =====
    order.checkout_session_id = session.id        # "cs_test_abc123"
    order.payment_intent_id = session.payment_intent
    order.status = "pending"  # Now awaiting payment
    
    db_session.add(order)
    db_session.commit()  # Save to database
    
    # Update database:
    # UPDATE orders SET
    #   checkout_session_id = 'cs_test_abc123',
    #   payment_intent_id = 'pi_test_xyz789',
    #   status = 'pending',
    #   updated_at = now()
    # WHERE id = 'ord_abc123'

    # ===== RETURN TO FRONTEND =====
    return CheckoutSessionResponse(
        id=order.id,
        checkout_session_id=session.id,
        url=session.url,  # Frontend redirects here!
        status=order.status,
    )
    # Returns: {
    #   "id": "ord_abc123",
    #   "checkout_session_id": "cs_test_abc123",
    #   "url": "https://checkout.stripe.com/pay/cs_test_abc123",
    #   "status": "pending"
    # }
```

### STEP 5: Frontend Redirects User to Stripe

**File:** `stripe-frontend/src/components/checkout/CheckoutForm.js`
```javascript
// Receiving the response from backend:
const { url } = response;  // "https://checkout.stripe.com/pay/cs_test_abc123"

// Redirect browser to Stripe's checkout page
window.location.href = url;

// User's browser navigates to Stripe
// User sees checkout page with:
// - Product: "Laptop"
// - Price: $1,000.00 (500 × 2)
// - Email: john@example.com
// - Card input field
```

### STEP 6: User Pays on Stripe Page

```
Stripe Hosted Checkout Page:
┌─────────────────────────────────┐
│ Laptop                  $1000.00 │
│ Quantity: 2                     │
│                                 │
│ john@example.com               │
│                                 │
│ Card Number: [4242 4242 4242...│
│ Expiry: [12/26]  CVC: [123]    │
│                                 │
│              [Pay] button       │
└─────────────────────────────────┘

User enters test card:
- 4242 4242 4242 4242
- Expiry: 12/26
- CVC: 123

Clicks [Pay] button

Stripe processes payment securely...
✅ Payment succeeds!
```

### STEP 7: Stripe Redirects User Back to Your App

**Stripe's redirect:**
```javascript
// Stripe knows success_url from Step 4:
// success_url = "http://localhost:3000/success?session_id=cs_test_abc123"

// After payment succeeds, Stripe redirects user's browser:
window.location.href = "http://localhost:3000/success?session_id=cs_test_abc123";

// User's browser navigates to your frontend success page
// App.js reads the URL and renders CheckoutSuccessPage
```

### STEP 8: Stripe Sends Webhook to Your Backend (Parallel)

**Happening at the same time as Step 7:**

Stripe's servers POST to your webhook endpoint:

```
POST http://localhost:8000/webhooks/stripe

Headers:
  Stripe-Signature: v1=abc123xyz...

Body (JSON):
{
  "id": "evt_1234567890",
  "type": "charge.succeeded",
  "api_version": "2024-03-22",
  "livemode": false,
  "created": 1710843330,
  "data": {
    "object": {
      "id": "ch_1234567890",
      "object": "charge",
      "status": "succeeded",
      "amount": 100000,
      "currency": "usd",
      "customer": null,
      "client_reference_id": "ord_abc123",    ← Links to order!
      "metadata": {
        "order_id": "ord_abc123",
        "product_name": "Laptop"
      },
      "payment_intent": "pi_test_xyz789"
    }
  }
}
```

### STEP 9: Backend Receives & Validates Webhook

**File:** `backend/app/api/routes/webhooks.py`
```python
@router.post("/webhooks/stripe", response_model=WebhookAckResponse)
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
    settings: AppSettings = Depends(get_settings),
    db_session: Session = Depends(get_db_session),
) -> WebhookAckResponse:
    """
    Stripe calls this endpoint when payment events happen
    """

    # ===== SECURITY: VERIFY SIGNATURE =====
    # Check: Is STRIPE_WEBHOOK_SECRET configured?
    if not settings.stripe_webhook_secret:
        raise HTTPException(
            status_code=500,
            detail="STRIPE_WEBHOOK_SECRET is not configured",
        )

    # Check: Did Stripe send the header?
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")

    # Get raw request body
    payload_bytes = await request.body()

    # Verify the signature matches our webhook secret
    # This proves the request really came from Stripe!
    try:
        event = stripe.Webhook.construct_event(
            payload=payload_bytes,
            sig_header=stripe_signature,
            secret=settings.stripe_webhook_secret,
            # If signature doesn't match, this throws SignatureVerificationError
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid webhook payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
        # ^^ Hacker tried to fake the webhook!

    # If we get here: ✅ Signature is valid, webhook is from Stripe

    # ===== PROCESS THE EVENT =====
    processor = StripeWebhookService()

    try:
        duplicate, event_id = processor.process_event(event, db_session)
        # Returns: (is_duplicate=False, event_id="evt_1234567890")
    except Exception as error:
        db_session.rollback()
        raise HTTPException(status_code=500, detail="Webhook processing failed")

    # ===== ACKNOWLEDGE TO STRIPE =====
    return WebhookAckResponse(
        received=True,
        duplicate=duplicate,
        event_id=event_id
    )
    # Returns 200 OK, which tells Stripe: "I got your message!"
```

### STEP 10: Service Processes Webhook Event

**File:** `backend/app/services/webhook_service.py`
```python
def process_event(self, event: stripe.Event, db_session: Session) -> tuple[bool, str]:
    """
    Process one webhook event idempotently.
    Returns: (is_duplicate, stripe_event_id)
    """

    event_id = event["id"]           # "evt_1234567890"
    event_type = event["type"]       # "charge.succeeded"

    # ===== IDEMPOTENCY CHECK =====
    # Have we processed this event before?
    duplicate_event = db_session.scalar(
        select(StripeWebhookEvent).where(
            StripeWebhookEvent.stripe_event_id == event_id
        )
    )
    
    if duplicate_event is not None:
        # Already processed! Return without doing anything
        return True, event_id
    
    # If we get here: This is a NEW event

    # ===== FIND THE ORDER =====
    event_object = event["data"]["object"]
    # event_object = {
    #   "id": "ch_1234567890",
    #   "client_reference_id": "ord_abc123",  ← Our order ID!
    #   "status": "succeeded",
    #   ...
    # }

    order = self._find_order_for_event(db_session, event_object)
    # Searches for order with ID = "ord_abc123"
    # Query: SELECT * FROM orders WHERE id = 'ord_abc123'
    # Returns: Order object

    if order is not None:
        # ===== UPDATE ORDER STATUS =====
        self._apply_order_updates(order, event_type, event_object)
        
        # _apply_order_updates checks event_type:
        if event_type == "charge.succeeded":
            order.status = "paid"
            order.paid_at = datetime.now(timezone.utc)
        elif event_type == "charge.failed":
            order.status = "payment_failed"
        elif event_type == "charge.expired":
            order.status = "expired"

        db_session.add(order)
        # UPDATE orders SET status='paid', paid_at=now() WHERE id='ord_abc123'

    # ===== LOG THE WEBHOOK EVENT =====
    event_log = StripeWebhookEvent(
        stripe_event_id=event_id,           # "evt_1234567890"
        event_type=event_type,              # "charge.succeeded"
        api_version=event.get("api_version"),
        livemode=bool(event.get("livemode")),
        order_id=order.id if order else None,
        payload_json=event.to_dict_recursive(),  # Store full event
        processing_error=None,
    )
    
    db_session.add(event_log)
    # INSERT INTO stripe_webhook_events (...)
    
    db_session.commit()  # Save both order update and event log
    
    return False, event_id  # Not a duplicate, successfully processed
```

### STEP 11: Database Gets Updated

```sql
-- Order gets updated:
UPDATE orders 
SET 
  status = 'paid',
  paid_at = '2024-03-22 10:15:30',
  updated_at = '2024-03-22 10:15:30'
WHERE id = 'ord_abc123';

-- Webhook event gets logged:
INSERT INTO stripe_webhook_events (
  stripe_event_id,
  event_type,
  order_id,
  payload_json,
  processed_at
) VALUES (
  'evt_1234567890',
  'charge.succeeded',
  'ord_abc123',
  '{...full event JSON...}',
  '2024-03-22 10:15:30'
);
```

### STEP 12: Frontend Success Page Loads

**File:** `stripe-frontend/src/pages/CheckoutSuccessPage.js`
```javascript
function CheckoutSuccessPage({ sessionId }) {
  const [orderData, setOrderData] = useState(null);
  const [loadingOrder, setLoadingOrder] = useState(false);

  // When component mounts, load order status from backend
  const loadOrderData = useCallback(async () => {
    if (!sessionId) {
      return;
    }

    setLoadingOrder(true);

    try {
      // Call backend to get order status
      const order = await fetchOrderBySessionId(sessionId);
      //     ↓
      //     GET /orders/by-session/cs_test_abc123
      
      setOrderData(order);
      // order = {
      //   "id": "ord_abc123",
      //   "status": "paid",           <- Updated by webhook!
      //   "total_amount": 100000,
      //   "paid_at": "2024-03-22T10:15:30"
      // }
      
    } catch (error) {
      setOrderMessage("Could not load order");
    }
  }, [sessionId]);

  useEffect(() => {
    loadOrderData();
  }, [loadOrderData]);

  return (
    <div className="success-page">
      <h1>Your payment was successful!</h1>
      {orderData && (
        <div>
          <p>Status: {orderData.status}</p>  {/* Shows "paid" */}
          <p>Amount: ${orderData.total_amount / 100}</p>  {/* Shows $1000.00 */}
          <p>Paid at: {orderData.paid_at}</p>
        </div>
      )}
    </div>
  );
}
```

### STEP 13: Backend Returns Order Status

**File:** `backend/app/api/routes/orders.py`
```python
@router.get("/orders/by-session/{checkout_session_id}", response_model=OrderResponse)
def get_order_by_checkout_session(
    checkout_session_id: str,
    settings: AppSettings = Depends(get_settings),
    db_session: Session = Depends(get_db_session),
) -> OrderResponse:
    """
    Frontend calls: GET /orders/by-session/cs_test_abc123
    """

    # Find order by Stripe session ID
    order = db_session.scalar(
        select(Order).where(Order.checkout_session_id == checkout_session_id)
        # Query: SELECT * FROM orders WHERE checkout_session_id='cs_test_abc123'
    )

    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    # If order is still pending, check with Stripe in case webhook was late
    order_service = OrderService(settings)
    order = order_service.sync_order_from_stripe(order, db_session)
    # If order.status == "pending":
    //   Ask Stripe: "What's the real status of this payment?"
    //   If Stripe says "succeeded", update order to "paid"

    # Return order to frontend
    return _to_order_response(order)
    # Returns:
    # {
    #   "id": "ord_abc123",
    #   "status": "paid",
    #   "product_name": "Laptop",
    #   "total_amount": 100000,
    #   "currency": "usd",
    #   "paid_at": "2024-03-22T10:15:30",
    #   "created_at": "2024-03-22T10:10:00"
    # }
```

### STEP 14: Frontend Displays Success

```
User sees:
┌─────────────────────────────┐
│  ✅ Payment Successful!      │
│                             │
│  Status: paid               │
│  Amount: $1,000.00          │
│  Date: Mar 22, 2024 10:15am │
│                             │
│  [Start New Payment]        │
└─────────────────────────────┘
```

---

## What Happens If Something Goes Wrong?

### Scenario 1: User Cancels Payment
```
1. User on Stripe page clicks X or "Cancel"
2. Stripe redirects to: http://localhost:3000/cancel
3. App.js renders CheckoutCancelPage
4. Order status in database stays "pending"
5. Stripe never sends "charge.succeeded" webhook
6. Order remains "pending" forever (or admin can mark it cancelled)
```

### Scenario 2: Webhook Gets Lost (Network Error)
```
1. Payment succeeds on Stripe's side
2. Webhook tries to POST to /webhooks/stripe but network dies
3. Stripe retries webhook (Stripe retries for 3 days!)
4. Eventually webhook arrives
5. Backend processes it and marks order "paid"
6. Meanwhile, if user went to success page:
   - Called GET /orders/by-session/{id}
   - Order status is still "pending"
   - OrderService.sync_order_from_stripe() checks Stripe directly
   - Finds payment succeeded, updates order to "paid"
   - Frontend shows "paid" even before webhook arrives!
```

### Scenario 3: Duplicate Webhook
```
1. Webhook arrives and gets processed
   UPDATE orders SET status='paid' WHERE id='ord_abc123'
   INSERT INTO stripe_webhook_events (stripe_event_id='evt_123')

2. Network issue, Stripe doesn't get HTTP 200 response

3. Stripe retries webhook (same event ID!)

4. Backend receives webhook again
   - Queries: SELECT * FROM stripe_webhook_events WHERE stripe_event_id='evt_123'
   - Finds existing record! (Duplicate!)
   - Returns 200 OK without updating order again
   - Order status is still "paid" (not "paid" twice)
```

---

## Database State Throughout Flow

```
BEFORE payment:
orders table:
  (empty)

AFTER /create-checkout-session:
orders table:
┌──────────────┬────────────┬──────────┐
│ id           │ status     │ session  │
├──────────────┼────────────┼──────────┤
│ ord_abc123   │ pending    │ cs_...   │
└──────────────┴────────────┴──────────┘

AFTER webhook received:
orders table:
┌──────────────┬────────────┬──────────┐
│ id           │ status     │ paid_at  │
├──────────────┼────────────┼──────────┤
│ ord_abc123   │ paid       │ 2024-... │
└──────────────┴────────────┴──────────┘

stripe_webhook_events table:
┌────────────────────┬──────────────────┬──────────────┐
│ stripe_event_id    │ event_type       │ order_id     │
├────────────────────┼──────────────────┼──────────────┤
│ evt_1234567890     │ charge.succeeded │ ord_abc123   │
└────────────────────┴──────────────────┴──────────────┘
```

---

## Complete Request/Response Example

```
========== REQUEST 1: Create Checkout Session ==========
POST /create-checkout-session HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "item": {
    "product_name": "Laptop",
    "unit_amount": 50000,
    "quantity": 2,
    "currency": "usd",
    "description": "MacBook Pro"
  },
  "customer_email": "john@example.com",
  "success_path": "/success",
  "cancel_path": "/cancel",
  "allow_promotion_codes": true
}

========== RESPONSE 1: Checkout Session Created ==========
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": "ord_abc123",
  "checkout_session_id": "cs_test_abcxyz",
  "url": "https://checkout.stripe.com/pay/cs_test_abcxyz",
  "status": "pending"
}

========== REQUEST 2: Webhook from Stripe ==========
POST /webhooks/stripe HTTP/1.1
Host: localhost:8000
Stripe-Signature: v1=abc123xyz...
Content-Type: application/json

{
  "id": "evt_1234567890",
  "type": "charge.succeeded",
  "api_version": "2024-03-22",
  "data": {
    "object": {
      "id": "ch_1234567890",
      "status": "succeeded",
      "amount": 100000,
      "currency": "usd",
      "client_reference_id": "ord_abc123",
      "metadata": {
        "order_id": "ord_abc123"
      }
    }
  }
}

========== RESPONSE 2: Webhook Acknowledged ==========
HTTP/1.1 200 OK
Content-Type: application/json

{
  "received": true,
  "duplicate": false,
  "event_id": "evt_1234567890"
}

========== REQUEST 3: Get Order Status ==========
GET /orders/by-session/cs_test_abcxyz HTTP/1.1
Host: localhost:8000

========== RESPONSE 3: Order Status ==========
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": "ord_abc123",
  "status": "paid",
  "product_name": "Laptop",
  "unit_amount": 50000,
  "quantity": 2,
  "total_amount": 100000,
  "currency": "usd",
  "description": "MacBook Pro",
  "customer_email": "john@example.com",
  "checkout_session_id": "cs_test_abcxyz",
  "failure_reason": null,
  "paid_at": "2024-03-22T10:15:30",
  "created_at": "2024-03-22T10:10:00",
  "updated_at": "2024-03-22T10:15:30"
}
```

---

**This is the complete journey! Every line of code has a purpose in this flow.** 🚀
