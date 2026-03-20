import React, { useEffect, useMemo, useState } from "react";

import {
  DEFAULT_CANCEL_PATH,
  DEFAULT_SUCCESS_PATH,
  SUPPORTED_CURRENCIES,
} from "./config/environment";
import CheckoutCancelPage from "./pages/CheckoutCancelPage";
import CheckoutStartPage from "./pages/CheckoutStartPage";
import CheckoutSuccessPage from "./pages/CheckoutSuccessPage";
import { createCheckoutSession, fetchCheckoutDefaults } from "./services/checkoutApi";
import "./styles/checkout.css";

/**
 * App-wide fallback form values used before backend defaults finish loading.
 */
const FALLBACK_FORM_VALUES = {
  productName: "",
  unitAmount: "",
  quantity: "1",
  currency: SUPPORTED_CURRENCIES[0],
  description: "",
  customerEmail: "",
  allowPromotionCodes: true,
};

/**
 * Conservative minimum totals in smallest currency units.
 * These values prevent common Stripe "minimum charge" errors.
 */
const MINIMUM_TOTAL_BY_CURRENCY = {
  usd: 50,
  eur: 50,
  gbp: 30,
  cad: 50,
  aud: 50,
  inr: 5000,
};

/**
 * Parse positive integer fields from text inputs.
 *
 * @param {string} rawValue - Input value from form state.
 * @param {string} label - Field name used in error messages.
 * @returns {number} Parsed positive integer.
 */
function parsePositiveInteger(rawValue, label) {
  const parsed = Number.parseInt(rawValue, 10);

  if (!Number.isFinite(parsed) || parsed <= 0) {
    throw new Error(`${label} must be a positive whole number.`);
  }

  return parsed;
}

/**
 * Build backend payload structure from frontend form fields.
 *
 * @param {typeof FALLBACK_FORM_VALUES} formValues - Current form values.
 * @returns {object} Request body expected by backend.
 */
function buildCheckoutPayload(formValues) {
  const amount = parsePositiveInteger(formValues.unitAmount, "Amount");
  const quantity = parsePositiveInteger(formValues.quantity, "Quantity");
  const currency = (formValues.currency || "").trim().toLowerCase();

  if (currency.length !== 3) {
    throw new Error("Currency must be a 3-letter code like usd or inr.");
  }

  const productName = (formValues.productName || "").trim();
  if (!productName) {
    throw new Error("Product name is required.");
  }

  const minimumTotal = MINIMUM_TOTAL_BY_CURRENCY[currency];
  if (minimumTotal && amount * quantity < minimumTotal) {
    throw new Error(
      `For ${currency.toUpperCase()}, total must be at least ${minimumTotal} in the smallest unit.`
    );
  }

  return {
    item: {
      product_name: productName,
      unit_amount: amount,
      quantity,
      currency,
      description: (formValues.description || "").trim() || null,
    },
    customer_email: (formValues.customerEmail || "").trim() || null,
    allow_promotion_codes: Boolean(formValues.allowPromotionCodes),
  };
}

/**
 * Main app controller that renders start/success/cancel pages.
 *
 * @returns {JSX.Element} Active page view based on current URL path.
 */
function App() {
  const [formValues, setFormValues] = useState(FALLBACK_FORM_VALUES);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const currentPath = useMemo(() => window.location.pathname.toLowerCase(), []);
  const queryParams = useMemo(() => new URLSearchParams(window.location.search), []);
  const sessionId = queryParams.get("session_id");
  const checkoutStatus = queryParams.get("checkout_status");

  const isSuccessPage =
    checkoutStatus === "success" || currentPath.startsWith(DEFAULT_SUCCESS_PATH);
  const isCancelPage =
    checkoutStatus === "cancelled" || currentPath.startsWith(DEFAULT_CANCEL_PATH);

  useEffect(() => {
    if (isSuccessPage || isCancelPage) {
      return;
    }

    /**
     * Load backend default values so frontend does not hardcode business data.
     */
    async function loadDefaults() {
      try {
        const defaults = await fetchCheckoutDefaults();
        setFormValues((currentValues) => ({
          ...currentValues,
          productName: defaults.product_name || currentValues.productName,
          unitAmount: String(defaults.unit_amount || currentValues.unitAmount),
          quantity: String(defaults.quantity || currentValues.quantity),
          currency: defaults.currency || currentValues.currency,
        }));
      } catch (error) {
        setMessage(error.message || "Could not load checkout defaults from backend.");
      }
    }

    loadDefaults();
  }, [isCancelPage, isSuccessPage]);

  /**
   * Update form state for text/select/checkbox controls.
   *
   * @param {string} name - Form field key.
   * @param {string | boolean} value - New field value.
   */
  const handleFieldChange = (name, value) => {
    setFormValues((currentValues) => ({ ...currentValues, [name]: value }));
  };

  /**
   * Send checkout payload to backend and redirect user to hosted Stripe URL.
   *
   * @param {React.FormEvent<HTMLFormElement>} event - Form submit event.
   * @returns {Promise<void>}
   */
  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setMessage("");

    try {
      const payload = buildCheckoutPayload(formValues);
      const session = await createCheckoutSession(payload);
      window.location.assign(session.url);
    } catch (error) {
      setMessage(error.message || "Unable to create checkout session.");
    } finally {
      setLoading(false);
    }
  };

  /**
   * Return user to form home page after success/cancel page.
   */
  const goToHome = () => {
    window.location.assign("/");
  };

  if (isSuccessPage) {
    return <CheckoutSuccessPage sessionId={sessionId} onPrimaryAction={goToHome} />;
  }

  if (isCancelPage) {
    return <CheckoutCancelPage onPrimaryAction={goToHome} />;
  }

  return (
    <CheckoutStartPage
      formValues={formValues}
      onFieldChange={handleFieldChange}
      onSubmit={handleSubmit}
      loading={loading}
      message={message}
      currencies={SUPPORTED_CURRENCIES}
    />
  );
}

export default App;
