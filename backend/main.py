# Import the stripe library so Python can communicate with Stripe's API
import stripe

# Import CORS middleware which allows frontend applications to access the backend
from fastapi.middleware.cors import CORSMiddleware

# Import FastAPI to create the backend web server
from fastapi import FastAPI

# Import load_dotenv to read environment variables from the .env file
from dotenv import load_dotenv

# Import os so Python can access environment variables
import os

# Import JSONResponse so the API can return JSON data
from fastapi.responses import JSONResponse

# Load variables from the .env file into the environment
load_dotenv()

# Retrieve the Stripe secret key from environment variables
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# Create a FastAPI application instance
app = FastAPI()

# Define which frontend origins are allowed to access the backend
origins = [
    "http://localhost:3000"
]

# Add CORS middleware to FastAPI
app.add_middleware(
    CORSMiddleware,

    # Allow the frontend origin
    allow_origins=origins,

    # Allow cookies if needed
    allow_credentials=True,

    # Allow all HTTP methods (GET, POST, etc.)
    allow_methods=["*"],

    # Allow all headers
    allow_headers=["*"],
)

# Define a route (endpoint) that runs when someone visits /create-customer
@app.get("/create-customer")
def create_customer():

    # Call Stripe's API to create a new customer object
    # stripe.Customer.create() sends a request to Stripe's servers
    customer = stripe.Customer.create(

        # Provide an email address for the customer being created
        email="testcustomer@example.com"
    )

    # Return the Stripe customer object as a JSON response
    # This allows us to see the created customer data in the browser
    return customer

# Define an API route that creates a PaymentIntent
@app.post("/create-payment-intent")
def create_payment_intent():

    # Create a PaymentIntent using Stripe's API
    payment_intent = stripe.PaymentIntent.create(

        # Amount to charge in the smallest currency unit
        # For USD this would be cents (example: 1000 = $10)
        amount=1000,

        # Currency used for the payment
        currency="usd",

        # Enable automatic payment method detection
        # Stripe automatically determines valid payment methods
        automatic_payment_methods={"enabled": True},
    )

    # Return the client secret to the frontend
    # The client secret allows the frontend to complete the payment
    return JSONResponse({
        "clientSecret": payment_intent.client_secret
    })


