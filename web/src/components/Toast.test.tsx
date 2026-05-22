import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render } from "@testing-library/react";
import { Toast } from "./Toast";

describe("Toast", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
    document.body.innerHTML = "";
  });

  it("renders nothing when toast is null", () => {
    const { container } = render(<Toast toast={null} />);
    expect(container.firstChild).toBeNull();
    // And nothing leaked into the portal target either.
    expect(document.body.querySelector('[role="status"]')).toBeNull();
  });

  it("renders the success message into the body via portal", () => {
    render(<Toast toast={{ message: "Saved", type: "success" }} />);
    const node = document.body.querySelector('[role="status"]');
    expect(node).not.toBeNull();
    expect(node!.textContent).toBe("Saved");
    expect(node!.className).toMatch(/text-success/);
  });

  it("applies error styling for error type", () => {
    render(<Toast toast={{ message: "Boom", type: "error" }} />);
    const node = document.body.querySelector('[role="status"]');
    expect(node!.className).toMatch(/text-destructive/);
  });

  it("uses aria-live=polite for accessibility", () => {
    render(<Toast toast={{ message: "hi", type: "success" }} />);
    const node = document.body.querySelector('[role="status"]');
    expect(node!.getAttribute("aria-live")).toBe("polite");
  });

  it("keeps the message mounted briefly after toast becomes null (animation out)", () => {
    const { rerender } = render(
      <Toast toast={{ message: "Saved", type: "success" }} />,
    );
    expect(document.body.querySelector('[role="status"]')!.textContent).toBe(
      "Saved",
    );
    rerender(<Toast toast={null} />);
    // Still present right after — the 200ms unmount timer hasn't fired yet.
    expect(document.body.querySelector('[role="status"]')).not.toBeNull();
  });
});
