import { render, screen } from "@testing-library/react";
import App from "./App";

/**
 * Basic smoke test to confirm the checkout form renders.
 */
test("renders checkout form heading", () => {
  render(<App />);
  const headingElement = screen.getByText(/build checkout from form data/i);
  expect(headingElement).toBeInTheDocument();
});
