import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, cleanup, waitFor } from "@testing-library/react";
import { RouterWrapper } from "@/test-helpers";

const apiMock = vi.hoisted(() => ({
  getLogs: vi.fn(),
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
vi.mock("@/i18n", () => ({
  useI18n: () => ({
    t: {
      app: {
        nav: {
          logs: "Logs",
          chat: "", sessions: "", analytics: "", models: "", cron: "",
          skills: "", plugins: "", profiles: "", config: "", keys: "",
          documentation: "",
        },
      },
      logs: {
        title: "Logs",
        file: "File",
        level: "Level",
        component: "Component",
        lines: "Lines",
        autoRefresh: "Auto refresh",
        refresh: "Refresh",
        empty: "No log entries.",
        error: "Error loading logs",
      },
      common: { loading: "Loading…" },
    },
  }),
}));
vi.mock("@/plugins", () => ({
  PluginSlot: () => null,
}));
// The design-language components only need to render *something* in jsdom —
// stub them so we don't pull in webgl/canvas/leva peer deps.
vi.mock("@nous-research/ui/ui/components/badge", () => ({
  Badge: ({ children }: { children: React.ReactNode }) => <span>{children}</span>,
}));
vi.mock("@nous-research/ui/ui/components/button", () => ({
  Button: ({ children, onClick, ...rest }: any) => (
    <button onClick={onClick} {...rest}>{children}</button>
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
vi.mock("@nous-research/ui/ui/components/segmented", () => ({
  Segmented: ({ value }: { value: string }) => <span data-segmented={value}>{value}</span>,
  FilterGroup: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

import LogsPage from "./LogsPage";

describe("LogsPage smoke", () => {
  beforeEach(() => {
    apiMock.getLogs.mockReset();
    headerStub.setTitle.mockClear();
    headerStub.setAfterTitle.mockClear();
    headerStub.setEnd.mockClear();
  });
  afterEach(() => cleanup());

  it("renders without crashing and calls api.getLogs on mount with defaults", async () => {
    apiMock.getLogs.mockResolvedValue({ lines: [] });
    render(
      <RouterWrapper>
        <LogsPage />
      </RouterWrapper>,
    );
    await waitFor(() => expect(apiMock.getLogs).toHaveBeenCalled());
    const args = apiMock.getLogs.mock.calls[0][0];
    expect(args).toMatchObject({
      file: "agent",
      lines: 100,
      level: "ALL",
      component: "all",
    });
  });

  it("renders fetched log lines into the scroll container", async () => {
    apiMock.getLogs.mockResolvedValue({
      lines: ["2026-05-22 INFO ready", "2026-05-22 ERROR boom"],
    });
    const { findByText } = render(
      <RouterWrapper>
        <LogsPage />
      </RouterWrapper>,
    );
    expect(await findByText(/INFO ready/)).toBeTruthy();
    expect(await findByText(/ERROR boom/)).toBeTruthy();
  });

  it("shows an error message when the API rejects", async () => {
    apiMock.getLogs.mockRejectedValue(new Error("network down"));
    const { findByText } = render(
      <RouterWrapper>
        <LogsPage />
      </RouterWrapper>,
    );
    expect(await findByText(/network down/)).toBeTruthy();
  });

  it("registers header chrome (after-title + end) via usePageHeader", () => {
    apiMock.getLogs.mockResolvedValue({ lines: [] });
    render(
      <RouterWrapper>
        <LogsPage />
      </RouterWrapper>,
    );
    // The page calls setAfterTitle and setEnd at least once during mount.
    expect(headerStub.setAfterTitle).toHaveBeenCalled();
    expect(headerStub.setEnd).toHaveBeenCalled();
  });
});
