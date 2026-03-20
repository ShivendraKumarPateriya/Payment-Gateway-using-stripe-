import React from "react";

/**
 * Controlled checkout form component.
 *
 * @param {object} props - Component props.
 * @param {object} props.formValues - Current form state.
 * @param {(name: string, value: string | boolean) => void} props.onFieldChange - Field change handler.
 * @param {(event: React.FormEvent<HTMLFormElement>) => void} props.onSubmit - Submit handler.
 * @param {boolean} props.loading - Whether checkout request is in progress.
 * @param {string} props.message - Optional user-visible message.
 * @param {string[]} props.currencies - Currency options to show in dropdown.
 * @returns {JSX.Element} Checkout form UI.
 */
function CheckoutForm({
  formValues,
  onFieldChange,
  onSubmit,
  loading,
  message,
  currencies,
}) {
  return (
    <section className="checkout-card">
      <div className="status-badge">Secure Stripe Checkout</div>
      <h1>Build Checkout From Form Data</h1>
      <p>
        Change values below, then click pay. Backend receives this form data and creates a
        Stripe session dynamically. Redirect paths are handled automatically by backend.
      </p>
      <p className="micro-note">
        Note: Stripe enforces minimum charge amounts. Example: for INR, keep total at least
        5000 (smallest unit).
      </p>

      <form className="checkout-form" onSubmit={onSubmit}>
        <label className="field-group" htmlFor="productName">
          Product Name
          <input
            id="productName"
            value={formValues.productName}
            onChange={(event) => onFieldChange("productName", event.target.value)}
            placeholder="Starter Plan"
            required
          />
        </label>

        <div className="field-row">
          <label className="field-group" htmlFor="unitAmount">
            Amount (smallest unit)
            <input
              id="unitAmount"
              type="number"
              min="1"
              value={formValues.unitAmount}
              onChange={(event) => onFieldChange("unitAmount", event.target.value)}
              required
            />
          </label>

          <label className="field-group" htmlFor="quantity">
            Quantity
            <input
              id="quantity"
              type="number"
              min="1"
              value={formValues.quantity}
              onChange={(event) => onFieldChange("quantity", event.target.value)}
              required
            />
          </label>
        </div>

        <div className="field-row">
          <label className="field-group" htmlFor="currency">
            Currency
            <select
              id="currency"
              value={formValues.currency}
              onChange={(event) => onFieldChange("currency", event.target.value)}
            >
              {currencies.map((currency) => (
                <option key={currency} value={currency}>
                  {currency.toUpperCase()}
                </option>
              ))}
            </select>
          </label>

          <label className="field-group" htmlFor="customerEmail">
            Customer Email (optional)
            <input
              id="customerEmail"
              type="email"
              value={formValues.customerEmail}
              onChange={(event) => onFieldChange("customerEmail", event.target.value)}
              placeholder="customer@example.com"
            />
          </label>
        </div>

        <label className="field-group" htmlFor="description">
          Description (optional)
          <textarea
            id="description"
            rows="2"
            value={formValues.description}
            onChange={(event) => onFieldChange("description", event.target.value)}
            placeholder="One-time payment for sample product"
          />
        </label>

        <label className="checkbox-row" htmlFor="allowPromotionCodes">
          <input
            id="allowPromotionCodes"
            type="checkbox"
            checked={formValues.allowPromotionCodes}
            onChange={(event) => onFieldChange("allowPromotionCodes", event.target.checked)}
          />
          Allow promotion codes in Stripe checkout
        </label>

        <button type="submit" className="cta-button" disabled={loading}>
          {loading ? "Redirecting..." : "Create Session & Pay"}
        </button>
      </form>

      {message ? <p className="error-message">{message}</p> : null}
    </section>
  );
}

export default CheckoutForm;
