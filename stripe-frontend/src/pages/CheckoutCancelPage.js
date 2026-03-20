import React from "react";
import CheckoutStatusCard from "../components/checkout/CheckoutStatusCard";

/**
 * Cancel page shown when user exits Stripe checkout before completing payment.
 *
 * @param {object} props - Component props.
 * @param {() => void} props.onPrimaryAction - Button handler to return to home.
 * @returns {JSX.Element} Cancel view.
 */
function CheckoutCancelPage({ onPrimaryAction }) {
  return (
    <main className="checkout-page">
      <CheckoutStatusCard
        variant="cancel"
        badge="Checkout Cancelled"
        title="No payment was taken"
        description="You can update the form and try again whenever you are ready."
        buttonLabel="Try Again"
        onButtonClick={onPrimaryAction}
      />
    </main>
  );
}

export default CheckoutCancelPage;
