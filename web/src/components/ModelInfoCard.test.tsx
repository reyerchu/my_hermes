import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, cleanup, waitFor } from "@testing-library/react";

const apiMock = vi.hoisted(() => ({
  getModelInfo: vi.fn(),
}));
vi.mock("@/lib/api", () => ({ api: apiMock }));
vi.mock("@nous-research/ui/ui/components/spinner", () => ({
  Spinner: () => <div data-testid="spinner" />,
}));

import { ModelInfoCard } from "./ModelInfoCard";

beforeEach(() => apiMock.getModelInfo.mockReset());
afterEach(() => cleanup());

describe("ModelInfoCard", () => {
  it("does NOT call api when currentModel is empty", () => {
    render(<ModelInfoCard currentModel="" />);
    expect(apiMock.getModelInfo).not.toHaveBeenCalled();
  });

  it("calls api.getModelInfo once when currentModel is set", async () => {
    apiMock.getModelInfo.mockResolvedValue({});
    render(<ModelInfoCard currentModel="claude-sonnet-4-6" />);
    await waitFor(() => expect(apiMock.getModelInfo).toHaveBeenCalledOnce());
  });

  it("shows the loading spinner before the fetch resolves", async () => {
    // Resolve on next microtask so the synchronous render captures the
    // loading state before the .finally hides the spinner.
    apiMock.getModelInfo.mockImplementation(
      () =>
        new Promise((r) => {
          setTimeout(() => r({}), 50);
        }),
    );
    const { getByTestId } = render(
      <ModelInfoCard currentModel="claude-sonnet-4-6" />,
    );
    expect(getByTestId("spinner")).toBeTruthy();
    // Wait for the deferred resolve so the test exits cleanly.
    await new Promise((r) => setTimeout(r, 100));
  });

  it("renders fetched model info (context window + capabilities)", async () => {
    apiMock.getModelInfo.mockResolvedValue({
      model: "claude-sonnet-4-6",
      effective_context_length: 200_000,
      config_context_length: 0,
      auto_context_length: 200_000,
      capabilities: { max_output_tokens: 64_000, supports_vision: true },
    });
    const { container } = render(
      <ModelInfoCard currentModel="claude-sonnet-4-6" />,
    );
    await waitFor(() =>
      expect(container.textContent).toContain("Context Window"),
    );
    expect(container.textContent).toContain("200K");
  });

  it("renders null when info is missing the model field", async () => {
    apiMock.getModelInfo.mockResolvedValue({
      effective_context_length: 0,
    });
    const { container } = render(<ModelInfoCard currentModel="m" />);
    await waitFor(() => expect(apiMock.getModelInfo).toHaveBeenCalled());
    expect(container.firstChild).toBeNull();
  });


  it("re-fetches when refreshKey changes", async () => {
    apiMock.getModelInfo.mockResolvedValue({});
    const { rerender } = render(
      <ModelInfoCard currentModel="model-a" refreshKey={1} />,
    );
    await waitFor(() => expect(apiMock.getModelInfo).toHaveBeenCalledTimes(1));
    rerender(<ModelInfoCard currentModel="model-a" refreshKey={2} />);
    await waitFor(() => expect(apiMock.getModelInfo).toHaveBeenCalledTimes(2));
  });

  it("does NOT re-fetch when neither model nor refreshKey changes", async () => {
    apiMock.getModelInfo.mockResolvedValue({});
    const { rerender } = render(
      <ModelInfoCard currentModel="m" refreshKey={1} />,
    );
    await waitFor(() => expect(apiMock.getModelInfo).toHaveBeenCalledTimes(1));
    rerender(<ModelInfoCard currentModel="m" refreshKey={1} />);
    expect(apiMock.getModelInfo).toHaveBeenCalledTimes(1);
  });
});
