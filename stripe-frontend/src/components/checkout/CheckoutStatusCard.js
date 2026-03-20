import React from "react";

/**
 * Reusable card for success and cancel screens after Stripe redirect.
 *
 * @param {object} props - Component props.
 * @param {"success" | "cancel"} props.variant - Visual variant used for card styling.
 * @param {string} props.badge - Small status badge text.
 * @param {string} props.title - Main headline text.
 * @param {string} props.description - Supporting message.
 * @param {string} props.buttonLabel - Button text.
 * @param {() => void} props.onButtonClick - Click handler.
 * @param {string | null} [props.sessionId] - Optional Stripe session id for debugging.
 * @returns {JSX.Element} Status card.
 */
function CheckoutStatusCard({
  variant,
  badge,
  title,
  description,
  buttonLabel,
  onButtonClick,
  sessionId,
}) {
  return (
    <section className={`checkout-card ${variant}-card`}>
      <div className="status-badge">{badge}</div>
      <h1>{title}</h1>
      <p>{description}</p>

      {sessionId ? <p className="session-id">Session: {sessionId}</p> : null}

      <button type="button" className="cta-button secondary" onClick={onButtonClick}>
        {buttonLabel}
      </button>
    </section>
  );
}

export default CheckoutStatusCard;
