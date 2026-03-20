import React from "react";
import CheckoutForm from "../components/checkout/CheckoutForm";

/**
 * Page component displayed on `/` to collect checkout parameters.
 *
 * @param {object} props - Props passed by the App controller.
 * @returns {JSX.Element} Checkout start page.
 */
function CheckoutStartPage(props) {
  return (
    <main className="checkout-page">
      <CheckoutForm {...props} />
    </main>
  );
}

export default CheckoutStartPage;
