import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, cleanup, waitFor } from "@testing-library/react";

const apiMock = vi.hoisted(() => ({
  startOAuthLogin: vi.fn(),
  submitOAuthPkce: vi.fn(),
  pollOAuthStatus: vi.fn(),
}));
vi.mock("@/lib/api", () => ({ api: apiMock }));
vi.mock("@/i18n", () => ({
  useI18n: () => ({
    t: {
      common: { close: "Close", cancel: "Cancel" },
      oauth: {
        title: "Connect",
        startingFlow: "Starting…",
        openProvider: "Open provider",
        copyCode: "Copy code",
        approved: "Approved",
        retry: "Retry",
        close: "Close",
        deviceCodeInstructions: "Open the URL and enter the code",
        pkceCallback: "Paste the callback URL after approving",
        approveInProvider: "Approve in {provider}",
        pasteCallback: "Paste callback URL here",
        submit: "Submit",
        pasting: "Submitting…",
        expiresIn: "Expires in {time}",
      },
    },
  }),
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
vi.mock("@/components/NouiTypography", () => ({
  H2: ({ children }: any) => <h2>{children}</h2>,
}));

import { OAuthLoginModal } from "./OAuthLoginModal";

const provider = {
  id: "github",
  name: "GitHub",
  flow: "device" as const,
  status: { logged_in: false },
};

beforeEach(() => {
  Object.values(apiMock).forEach((m: any) => m.mockReset());
  // Prevent the component from popping a real window during the test.
  vi.stubGlobal("open", vi.fn());
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("OAuthLoginModal", () => {
  it("calls api.startOAuthLogin with the provider id on mount", async () => {
    apiMock.startOAuthLogin.mockImplementation(
      () => new Promise(() => {}),
    );
    render(
      <OAuthLoginModal
        provider={provider as any}
        onClose={() => {}}
        onSuccess={() => {}}
        onError={() => {}}
      />,
    );
    await waitFor(() =>
      expect(apiMock.startOAuthLogin).toHaveBeenCalledWith("github"),
    );
  });

  it("shows a spinner while starting", () => {
    apiMock.startOAuthLogin.mockImplementation(
      () => new Promise(() => {}),
    );
    const { getByTestId } = render(
      <OAuthLoginModal
        provider={provider as any}
        onClose={() => {}}
        onSuccess={() => {}}
        onError={() => {}}
      />,
    );
    expect(getByTestId("spinner")).toBeTruthy();
  });

  it("opens an external window after the start response resolves (device flow)", async () => {
    apiMock.startOAuthLogin.mockResolvedValue({
      flow: "device_code",
      verification_url: "https://github.com/login/device",
      user_code: "ABCD-1234",
      expires_in: 600,
    });
    const winOpen = window.open as unknown as ReturnType<typeof vi.fn>;
    render(
      <OAuthLoginModal
        provider={provider as any}
        onClose={() => {}}
        onSuccess={() => {}}
        onError={() => {}}
      />,
    );
    await waitFor(() =>
      expect(winOpen).toHaveBeenCalledWith(
        "https://github.com/login/device",
        "_blank",
        "noopener,noreferrer",
      ),
    );
  });

  it("opens auth_url for the pkce flow", async () => {
    apiMock.startOAuthLogin.mockResolvedValue({
      flow: "pkce",
      auth_url: "https://github.com/oauth/authorize?...",
      expires_in: 300,
    });
    const winOpen = window.open as unknown as ReturnType<typeof vi.fn>;
    render(
      <OAuthLoginModal
        provider={provider as any}
        onClose={() => {}}
        onSuccess={() => {}}
        onError={() => {}}
      />,
    );
    await waitFor(() =>
      expect(winOpen).toHaveBeenCalledWith(
        "https://github.com/oauth/authorize?...",
        "_blank",
        "noopener,noreferrer",
      ),
    );
  });
});
