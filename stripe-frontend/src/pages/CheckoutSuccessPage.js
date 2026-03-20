import React from "react";
import CheckoutStatusCard from "../components/checkout/CheckoutStatusCard";

/**
 * Success page shown after Stripe redirects user back after payment completion.
 *
 * @param {object} props - Component props.
 * @param {string | null} props.sessionId - Session ID in URL query string.
 * @param {() => void} props.onPrimaryAction - Button handler to return to home.
 * @returns {JSX.Element} Success view.
 */
function CheckoutSuccessPage({ sessionId, onPrimaryAction }) {
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
      />
    </main>
  );
}

export default CheckoutSuccessPage;
