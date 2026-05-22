import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, cleanup, waitFor } from "@testing-library/react";
import { RouterWrapper, makeTranslationStub } from "@/test-helpers";

const apiMock = vi.hoisted(() => ({
  getConfig: vi.fn(),
  getSchema: vi.fn(),
  getDefaults: vi.fn(),
  getStatus: vi.fn(),
  saveConfig: vi.fn(),
  saveConfigRaw: vi.fn(),
}));
const headerStub = vi.hoisted(() => ({
  setTitle: vi.fn(), setAfterTitle: vi.fn(), setEnd: vi.fn(),
}));

vi.mock("@/lib/api", () => ({ api: apiMock }));
vi.mock("@/contexts/usePageHeader", () => ({ usePageHeader: () => headerStub }));
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
vi.mock("@nous-research/ui/ui/components/segmented", () => ({
  Segmented: ({ value }: { value: string }) => <span>{value}</span>,
  FilterGroup: ({ children }: any) => <div>{children}</div>,
}));
vi.mock("@nous-research/ui/ui/components/select", () => ({
  Select: ({ children, value, onChange }: any) => (
    <select value={value} onChange={(e) => onChange?.(e.target.value)}>{children}</select>
  ),
  SelectOption: ({ value, children }: any) => <option value={value}>{children}</option>,
}));
vi.mock("@nous-research/ui/ui/components/switch", () => ({
  Switch: ({ checked, onCheckedChange }: any) => (
    <input type="checkbox" role="switch" checked={checked} onChange={(e) => onCheckedChange?.(e.target.checked)} />
  ),
}));
vi.mock("@nous-research/ui/ui/components/list-item", () => ({
  ListItem: ({ children }: any) => <div>{children}</div>,
}));

import ConfigPage from "./ConfigPage";

describe("ConfigPage smoke", () => {
  beforeEach(() => Object.values(apiMock).forEach((m: any) => m.mockReset()));
  afterEach(() => cleanup());

  it("calls api.getConfig on mount", async () => {
    apiMock.getConfig.mockResolvedValue({});
    apiMock.getSchema.mockResolvedValue({ fields: {}, category_order: [] });
    apiMock.getDefaults.mockResolvedValue({});
    apiMock.getStatus.mockResolvedValue({ gateway: { status: "ok" } });
    render(
      <RouterWrapper>
        <ConfigPage />
      </RouterWrapper>,
    );
    await waitFor(() => expect(apiMock.getConfig).toHaveBeenCalled());
  });

  it("does not crash when both fetches resolve empty", async () => {
    apiMock.getConfig.mockResolvedValue({});
    apiMock.getSchema.mockResolvedValue({ fields: {}, category_order: [] });
    apiMock.getDefaults.mockResolvedValue({});
    apiMock.getStatus.mockResolvedValue({ gateway: { status: "ok" } });
    expect(() =>
      render(
        <RouterWrapper>
          <ConfigPage />
        </RouterWrapper>,
      ),
    ).not.toThrow();
  });

  it("recovers gracefully when getConfig rejects", async () => {
    apiMock.getConfig.mockRejectedValue(new Error("offline"));
    apiMock.getSchema.mockRejectedValue(new Error("offline"));
    apiMock.getDefaults.mockRejectedValue(new Error("offline"));
    apiMock.getStatus.mockRejectedValue(new Error("offline"));
    expect(() =>
      render(
        <RouterWrapper>
          <ConfigPage />
        </RouterWrapper>,
      ),
    ).not.toThrow();
    await waitFor(() => expect(apiMock.getConfig).toHaveBeenCalled());
  });
});
