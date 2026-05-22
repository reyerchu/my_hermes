import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, cleanup, waitFor } from "@testing-library/react";
import { makeTranslationStub } from "@/test-helpers";

const apiMock = vi.hoisted(() => ({
  getOAuthProviders: vi.fn(),
  disconnectOAuthProvider: vi.fn(),
}));
vi.mock("@/lib/api", () => ({ api: apiMock }));
vi.mock("@/i18n", () => ({ useI18n: () => ({ t: makeTranslationStub() }) }));
vi.mock("@nous-research/ui/ui/components/badge", () => ({
  Badge: ({ children }: any) => <span>{children}</span>,
}));
vi.mock("@nous-research/ui/ui/components/button", () => ({
  Button: ({ children, onClick, disabled }: any) => (
    <button onClick={onClick} disabled={disabled}>{children}</button>
  ),
}));
vi.mock("@nous-research/ui/ui/components/command-block", () => ({
  CopyButton: () => null,
}));
vi.mock("@nous-research/ui/ui/components/spinner", () => ({
  Spinner: () => <div data-testid="spinner" />,
}));
vi.mock("./OAuthLoginModal", () => ({
  OAuthLoginModal: () => null,
}));

import { OAuthProvidersCard } from "./OAuthProvidersCard";

beforeEach(() => {
  apiMock.getOAuthProviders.mockReset();
  apiMock.disconnectOAuthProvider.mockReset();
});
afterEach(() => cleanup());

describe("OAuthProvidersCard smoke", () => {
  it("calls api.getOAuthProviders on mount", async () => {
    apiMock.getOAuthProviders.mockResolvedValue({ providers: [] });
    render(<OAuthProvidersCard />);
    await waitFor(() => expect(apiMock.getOAuthProviders).toHaveBeenCalled());
  });

  it("renders provider names from the API response", async () => {
    apiMock.getOAuthProviders.mockResolvedValue({
      providers: [
        {
          id: "github",
          name: "GitHub",
          flow: "device",
          status: { logged_in: false },
        },
        {
          id: "gitlab",
          name: "GitLab",
          flow: "device",
          status: { logged_in: true, token_preview: "abc..." },
        },
      ],
    });
    const { container } = render(<OAuthProvidersCard />);
    await waitFor(() => expect(apiMock.getOAuthProviders).toHaveBeenCalled());
    await waitFor(() => expect(container.textContent).toContain("GitHub"));
    expect(container.textContent).toContain("GitLab");
  });

  it("invokes onError when the load rejects", async () => {
    apiMock.getOAuthProviders.mockImplementation(
      () =>
        new Promise((_, reject) =>
          setTimeout(() => reject(new Error("offline")), 0),
        ),
    );
    const onError = vi.fn();
    render(<OAuthProvidersCard onError={onError} />);
    await waitFor(() => expect(onError).toHaveBeenCalled());
    expect(onError.mock.calls[0][0]).toMatch(/Failed to load/);
  });
});
