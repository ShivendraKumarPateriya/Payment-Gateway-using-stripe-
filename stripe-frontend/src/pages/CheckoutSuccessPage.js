import React, { useCallback, useEffect, useState } from "react";
import CheckoutStatusCard from "../components/checkout/CheckoutStatusCard";
import { fetchOrderBySessionId } from "../services/checkoutApi";

/**
 * Success page shown after Stripe redirects user back after payment completion.
 *
 * @param {object} props - Component props.
 * @param {string | null} props.sessionId - Session ID in URL query string.
 * @param {() => void} props.onPrimaryAction - Button handler to return to home.
 * @returns {JSX.Element} Success view.
 */
function CheckoutSuccessPage({ sessionId, onPrimaryAction }) {
  const [orderData, setOrderData] = useState(null);
  const [loadingOrder, setLoadingOrder] = useState(false);
  const [orderMessage, setOrderMessage] = useState("");

  /**
   * Load persisted order row from backend to confirm webhook/database flow.
   */
  const loadOrderData = useCallback(async () => {
    if (!sessionId) {
      setOrderMessage("Session ID missing in URL.");
      return;
    }

    setLoadingOrder(true);
    setOrderMessage("");

    try {
      const order = await fetchOrderBySessionId(sessionId);
      setOrderData(order);
    } catch (error) {
      setOrderMessage(error.message || "Could not load order status from backend.");
    } finally {
      setLoadingOrder(false);
    }
  }, [sessionId]);

  useEffect(() => {
    loadOrderData();
  }, [loadOrderData]);

  return (
    <main className="checkout-page">
      <CheckoutStatusCard
        variant="success"
        badge="Payment Completed"
        title="Your payment was successful"
        description="Thanks! Your transaction is complete and you can continue safely."
        sessionId={sessionId}
        buttonLabel="Start New Payment"
        onButtonClick={onPrimaryAction}
      >
        <div className="order-status-panel">
          <h3>Database Order Status</h3>
          {loadingOrder ? <p>Checking order status...</p> : null}
          {!loadingOrder && orderData ? (
            <>
              <p>Status: {orderData.status}</p>
              <p>Order ID: {orderData.id}</p>
              <p>
                Amount: {orderData.total_amount} ({orderData.currency.toUpperCase()})
              </p>
            </>
          ) : null}
          {!loadingOrder && orderMessage ? <p className="error-message">{orderMessage}</p> : null}

          <button type="button" className="inline-link-button" onClick={loadOrderData}>
            Refresh Order Status
          </button>
        </div>
      </CheckoutStatusCard>
    </main>
  );
}

export default CheckoutSuccessPage;
