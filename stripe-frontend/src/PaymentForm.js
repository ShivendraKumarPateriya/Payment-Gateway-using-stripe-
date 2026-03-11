// Import React library to create components
import React, { useState } from "react";

// Import Stripe hooks used to access Stripe functionality inside React
import { useStripe, useElements, CardElement } from "@stripe/react-stripe-js";

// Define a React component called PaymentForm
const PaymentForm = () => {

  // useStripe hook gives access to the Stripe object
  const stripe = useStripe();

  // useElements gives access to the Stripe Elements instance
  const elements = useElements();

  // State variable to track loading state during payment processing
  const [loading, setLoading] = useState(false);

  // State variable to store error messages
  const [message, setMessage] = useState("");

  // Function that runs when the payment form is submitted
  const handleSubmit = async (event) => {

    // Prevent the browser from refreshing the page
    event.preventDefault();

    // Set loading state to true
    setLoading(true);

    // Send request to backend to create PaymentIntent
    const response = await fetch("http://localhost:8000/create-payment-intent", {
      method: "POST"
    });

    // Convert response into JSON format
    const data = await response.json();

    // Extract the client secret returned by the backend
    const clientSecret = data.clientSecret;

    // Get the card input element created by Stripe
    const cardElement = elements.getElement(CardElement);

    // Confirm the payment using Stripe
    const result = await stripe.confirmCardPayment(clientSecret, {
      payment_method: {
        card: cardElement
      }
    });

    // If an error occurs during payment
    if (result.error) {

      // Display error message
      setMessage(result.error.message);

    } else {

      // Check if payment succeeded
      if (result.paymentIntent.status === "succeeded") {

        // Display success message
        setMessage("Payment successful!");

      }

    }

    // Set loading back to false
    setLoading(false);

  };

  return (

    <div style={{
      width: "400px",
      margin: "auto",
      padding: "30px",
      borderRadius: "10px",
      boxShadow: "0 4px 20px rgba(0,0,0,0.1)"
    }}>

      <h2 style={{textAlign:"center"}}>Stripe Payment</h2>

      <form onSubmit={handleSubmit}>

        <div style={{
          padding: "10px",
          border: "1px solid #ccc",
          borderRadius: "5px",
          marginBottom: "20px"
        }}>

          <CardElement />

        </div>

        <button
          disabled={!stripe || loading}
          style={{
            width: "100%",
            padding: "12px",
            background: "#635BFF",
            color: "white",
            border: "none",
            borderRadius: "6px",
            cursor: "pointer"
          }}
        >
          {loading ? "Processing..." : "Pay"}
        </button>

      </form>

      {message && (
        <p style={{marginTop:"15px", textAlign:"center"}}>
          {message}
        </p>
      )}

    </div>

  );

};

// Export component so it can be used in App.js
export default PaymentForm;