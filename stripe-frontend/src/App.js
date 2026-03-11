
// Import React
import React from "react";

// Import Stripe loader
import { loadStripe } from "@stripe/stripe-js";

// Import Stripe Elements wrapper
import { Elements } from "@stripe/react-stripe-js";

// Import the payment form component
import PaymentForm from "./PaymentForm";

// Load Stripe using the publishable key from .env in frontend
const stripePromise = loadStripe(process.env.REACT_APP_STRIPE_PUBLIC_KEY);

function App() {

  return (

    <div style={{
      height: "100vh",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      background: "#f5f6fa"
    }}>

      <Elements stripe={stripePromise}>

        <PaymentForm />

      </Elements>

    </div>

  );

}

export default App;
