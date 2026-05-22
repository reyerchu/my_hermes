import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, cleanup, waitFor } from "@testing-library/react";
import { RouterWrapper, makeTranslationStub } from "@/test-helpers";

const apiMock = vi.hoisted(() => ({
  getPluginsHub: vi.fn(),
  enableAgentPlugin: vi.fn(),
  disableAgentPlugin: vi.fn(),
  installAgentPlugin: vi.fn(),
  removeAgentPlugin: vi.fn(),
  updateAgentPlugin: vi.fn(),
  rescanPlugins: vi.fn(),
  setPluginVisibility: vi.fn(),
  savePluginProviders: vi.fn(),
}));
const headerStub = vi.hoisted(() => ({
  setTitle: vi.fn(),
  setAfterTitle: vi.fn(),
  setEnd: vi.fn(),
}));

vi.mock("@/lib/api", () => ({ api: apiMock }));
vi.mock("@/contexts/usePageHeader", () => ({
  usePageHeader: () => headerStub,
}));
vi.mock("@/i18n", () => ({ useI18n: () => ({ t: makeTranslationStub() }) }));
vi.mock("@/plugins", () => ({ PluginSlot: () => null }));
vi.mock("@nous-research/ui/ui/components/badge", () => ({
  Badge: ({ children }: any) => <span>{children}</span>,
}));
vi.mock("@nous-research/ui/ui/components/button", () => ({
  Button: ({ children, onClick, disabled }: any) => (
    <button onClick={onClick} disabled={disabled}>{children}</button>
  ),
}));
vi.mock("@nous-research/ui/ui/components/spinner", () => ({
  Spinner: () => <div data-testid="spinner" />,
}));
vi.mock("@nous-research/ui/ui/components/switch", () => ({
  Switch: ({ checked, onCheckedChange }: any) => (
    <input
      type="checkbox"
      role="switch"
      checked={checked}
      onChange={(e) => onCheckedChange?.(e.target.checked)}
    />
  ),
}));
vi.mock("@nous-research/ui/ui/components/select", () => ({
  Select: ({ children, value, onChange }: any) => (
    <select value={value} onChange={(e) => onChange?.(e.target.value)}>
      {children}
    </select>
  ),
  SelectOption: ({ value, children }: any) => <option value={value}>{children}</option>,
}));
vi.mock("@nous-research/ui/ui/components/command-block", () => ({
  CommandBlock: ({ command }: any) => <code>{command}</code>,
}));

import PluginsPage from "./PluginsPage";

const hubFixture = {
  plugins: [],
  orphan_dashboard_plugins: [],
  providers: {
    memory_provider: null,
    memory_options: [],
    context_engine: "compressor",
    context_options: [],
  },
};

describe("PluginsPage smoke", () => {
  beforeEach(() => {
    Object.values(apiMock).forEach((m: any) => m.mockReset());
    headerStub.setEnd.mockClear();
  });
  afterEach(() => cleanup());

  it("calls api.getPluginsHub on mount", async () => {
    apiMock.getPluginsHub.mockResolvedValue(hubFixture);
    render(
      <RouterWrapper>
        <PluginsPage />
      </RouterWrapper>,
    );
    await waitFor(() => expect(apiMock.getPluginsHub).toHaveBeenCalledOnce());
  });

  it("does not crash on empty hub response", async () => {
    apiMock.getPluginsHub.mockResolvedValue(hubFixture);
    expect(() =>
      render(
        <RouterWrapper>
          <PluginsPage />
        </RouterWrapper>,
      ),
    ).not.toThrow();
  });

  it("recovers when getPluginsHub rejects", async () => {
    apiMock.getPluginsHub.mockRejectedValue(new Error("offline"));
    expect(() =>
      render(
        <RouterWrapper>
          <PluginsPage />
        </RouterWrapper>,
      ),
    ).not.toThrow();
    await waitFor(() => expect(apiMock.getPluginsHub).toHaveBeenCalled());
  });
});
