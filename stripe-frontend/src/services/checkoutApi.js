import { API_BASE_URL } from "../config/environment";

/**
 * Execute a fetch request with timeout protection so UI does not hang forever.
 *
 * @param {string} url - Request URL.
 * @param {RequestInit} [options] - Fetch options.
 * @param {number} [timeoutMs=15000] - Timeout duration in milliseconds.
 * @returns {Promise<Response>} Raw fetch response.
 */
async function fetchWithTimeout(url, options = {}, timeoutMs = 15000) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error("Backend request timed out. Please verify the backend is running.");
    }

    throw new Error("Could not connect to backend. Please start backend server.");
  } finally {
    window.clearTimeout(timeoutId);
  }
}

/**
 * Parse API responses safely and convert backend errors into readable messages.
 *
 * @param {Response} response - Fetch API response object.
 * @returns {Promise<object>} Parsed JSON payload.
 */
async function parseJsonResponse(response) {
  const rawBody = await response.text();

  let payload = {};
  if (rawBody) {
    try {
      payload = JSON.parse(rawBody);
    } catch (error) {
      throw new Error("Server returned an unexpected response format.");
    }
  }

  if (!response.ok) {
    throw new Error(payload.detail || "Request failed. Please try again.");
  }

  return payload;
}

/**
 * Request default checkout values from backend.
 *
 * @returns {Promise<{product_name: string, unit_amount: number, quantity: number, currency: string}>}
 */
export async function fetchCheckoutDefaults() {
  const response = await fetchWithTimeout(`${API_BASE_URL}/checkout-defaults`);
  return parseJsonResponse(response);
}

/**
 * Create a new Stripe Checkout Session.
 *
 * @param {object} payload - Validated checkout payload ready for backend.
 * @returns {Promise<{id: string, url: string, order_id: string}>} Stripe checkout session data.
 */
export async function createCheckoutSession(payload) {
  const response = await fetchWithTimeout(`${API_BASE_URL}/create-checkout-session`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  return parseJsonResponse(response);
}

/**
 * Fetch persisted order state using Stripe Checkout Session ID.
 *
 * @param {string} sessionId - Stripe checkout session ID from success URL.
 * @returns {Promise<object>} Order row saved in backend database.
 */
export async function fetchOrderBySessionId(sessionId) {
  const encodedSessionId = encodeURIComponent(sessionId);
  const response = await fetchWithTimeout(`${API_BASE_URL}/orders/by-session/${encodedSessionId}`);
  return parseJsonResponse(response);
}
