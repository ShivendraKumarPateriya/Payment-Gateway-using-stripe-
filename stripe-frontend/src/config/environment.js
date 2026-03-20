/**
 * Frontend runtime configuration values.
 *
 * All values can be overridden with `.env` variables so we avoid hardcoding
 * deployment-specific settings in source files.
 */
export const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || "http://localhost:8000";

/**
 * Default app routes used after Stripe redirects users back to frontend.
 */
export const DEFAULT_SUCCESS_PATH = "/success";
export const DEFAULT_CANCEL_PATH = "/cancel";

/**
 * Currency options exposed in the checkout form.
 */
export const SUPPORTED_CURRENCIES = ["usd", "eur", "inr", "gbp", "cad", "aud"];
