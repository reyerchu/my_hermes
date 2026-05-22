import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, cleanup, waitFor } from "@testing-library/react";
import { RouterWrapper, makeTranslationStub } from "@/test-helpers";

const apiMock = vi.hoisted(() => ({
  getEnvVars: vi.fn(),
  setEnvVar: vi.fn(),
  deleteEnvVar: vi.fn(),
  revealEnvVar: vi.fn(),
}));
const headerStub = vi.hoisted(() => ({
  setTitle: vi.fn(), setAfterTitle: vi.fn(), setEnd: vi.fn(),
}));

vi.mock("@/lib/api", () => ({ api: apiMock }));
vi.mock("@/contexts/usePageHeader", () => ({ usePageHeader: () => headerStub }));
vi.mock("@/i18n", () => ({ useI18n: () => ({ t: makeTranslationStub() }) }));
vi.mock("@/plugins", () => ({ PluginSlot: () => null }));
vi.mock("@/components/OAuthProvidersCard", () => ({
  OAuthProvidersCard: () => null,
}));
vi.mock("@nous-research/ui/ui/components/badge", () => ({
  Badge: ({ children }: any) => <span>{children}</span>,
}));
vi.mock("@nous-research/ui/ui/components/button", () => ({
  Button: ({ children, onClick }: any) => <button onClick={onClick}>{children}</button>,
}));
vi.mock("@nous-research/ui/ui/components/list-item", () => ({
  ListItem: ({ children }: any) => <div>{children}</div>,
}));
vi.mock("@nous-research/ui/ui/components/spinner", () => ({
  Spinner: () => <div data-testid="spinner" />,
}));

import EnvPage from "./EnvPage";

describe("EnvPage smoke", () => {
  beforeEach(() => Object.values(apiMock).forEach((m: any) => m.mockReset()));
  afterEach(() => cleanup());

  it("calls api.getEnvVars on mount", async () => {
    apiMock.getEnvVars.mockResolvedValue({ vars: [] });
    render(
      <RouterWrapper>
        <EnvPage />
      </RouterWrapper>,
    );
    await waitFor(() => expect(apiMock.getEnvVars).toHaveBeenCalled());
  });

  it("does not crash when getEnvVars rejects", async () => {
    apiMock.getEnvVars.mockRejectedValue(new Error("offline"));
    expect(() =>
      render(
        <RouterWrapper>
          <EnvPage />
        </RouterWrapper>,
      ),
    ).not.toThrow();
    await waitFor(() => expect(apiMock.getEnvVars).toHaveBeenCalled());
  });
});
