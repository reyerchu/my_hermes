import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, cleanup, waitFor } from "@testing-library/react";
import { RouterWrapper, makeTranslationStub } from "@/test-helpers";

const apiMock = vi.hoisted(() => ({
  getSessions: vi.fn(),
  getStatus: vi.fn(),
  searchSessions: vi.fn(),
  deleteSession: vi.fn(),
}));
const headerStub = vi.hoisted(() => ({
  setTitle: vi.fn(), setAfterTitle: vi.fn(), setEnd: vi.fn(),
}));
const systemActionsStub = vi.hoisted(() => ({
  activeAction: null as null | "restart" | "update",
  actionStatus: null,
  dismissLog: vi.fn(),
  isBusy: false,
  isRunning: false,
  pendingAction: null,
  runAction: vi.fn(),
}));

vi.mock("@/lib/api", () => ({ api: apiMock }));
vi.mock("@/contexts/usePageHeader", () => ({ usePageHeader: () => headerStub }));
vi.mock("@/contexts/useSystemActions", () => ({
  useSystemActions: () => systemActionsStub,
}));
vi.mock("@/i18n", () => ({ useI18n: () => ({ t: makeTranslationStub() }) }));
vi.mock("@/plugins", () => ({ PluginSlot: () => null }));
// Heavy / DS-dependent components — stub to keep the smoke test honest.
vi.mock("@/components/Markdown", () => ({
  Markdown: ({ children }: any) => <div>{children}</div>,
}));
vi.mock("@/components/PlatformsCard", () => ({ PlatformsCard: () => null }));
vi.mock("@/components/Toast", () => ({ Toast: () => null }));
vi.mock("@/components/DeleteConfirmDialog", () => ({
  DeleteConfirmDialog: ({ open }: { open: boolean }) =>
    open ? <div data-testid="delete-dialog" /> : null,
}));
vi.mock("@nous-research/ui/ui/components/badge", () => ({
  Badge: ({ children }: any) => <span>{children}</span>,
}));
vi.mock("@nous-research/ui/ui/components/button", () => ({
  Button: ({ children, onClick, disabled }: any) => (
    <button onClick={onClick} disabled={disabled}>{children}</button>
  ),
}));
vi.mock("@nous-research/ui/ui/components/list-item", () => ({
  ListItem: ({ children, onClick }: any) => (
    <div role="listitem" onClick={onClick}>{children}</div>
  ),
}));
vi.mock("@nous-research/ui/ui/components/spinner", () => ({
  Spinner: () => <div data-testid="spinner" />,
}));

import SessionsPage from "./SessionsPage";

const sessionFixture = {
  id: "session-1",
  title: "Test session",
  origin_platform: "telegram",
  start_time: new Date().toISOString(),
  last_updated: new Date().toISOString(),
  message_count: 3,
  tool_count: 2,
  model: "claude-sonnet-4-6",
};

const statusFixture = {
  gateway: { status: "ok", uptime_seconds: 100 },
  platforms: [],
};

describe("SessionsPage smoke", () => {
  beforeEach(() => {
    Object.values(apiMock).forEach((m: any) => m.mockReset());
    // Default: every endpoint resolves with a usable payload.  Individual
    // tests override these as needed.
    apiMock.getSessions.mockResolvedValue({ sessions: [], total: 0 });
    apiMock.getStatus.mockResolvedValue(statusFixture);
    apiMock.searchSessions.mockResolvedValue({ results: [] });
    apiMock.deleteSession.mockResolvedValue({ ok: true });
  });
  afterEach(() => cleanup());

  it("calls api.getSessions for the first page on mount", async () => {
    render(
      <RouterWrapper>
        <SessionsPage />
      </RouterWrapper>,
    );
    await waitFor(() => expect(apiMock.getSessions).toHaveBeenCalled());
    // PAGE_SIZE is the first arg, page-offset (0 on mount) the second.
    const args = apiMock.getSessions.mock.calls[0];
    expect(args[1]).toBe(0);
  });

  it("calls api.getStatus on mount for the overview", async () => {
    render(
      <RouterWrapper>
        <SessionsPage />
      </RouterWrapper>,
    );
    await waitFor(() => expect(apiMock.getStatus).toHaveBeenCalled());
  });

  it("renders a session row from the API response", async () => {
    apiMock.getSessions.mockResolvedValue({
      sessions: [sessionFixture],
      total: 1,
    });
    const { container } = render(
      <RouterWrapper>
        <SessionsPage />
      </RouterWrapper>,
    );
    await waitFor(() => expect(apiMock.getSessions).toHaveBeenCalled());
    await waitFor(() =>
      expect(container.textContent).toContain("Test session"),
    );
  });

  it("does not crash when all endpoints reject", async () => {
    apiMock.getSessions.mockRejectedValue(new Error("offline"));
    apiMock.getStatus.mockRejectedValue(new Error("offline"));
    expect(() =>
      render(
        <RouterWrapper>
          <SessionsPage />
        </RouterWrapper>,
      ),
    ).not.toThrow();
    await waitFor(() => expect(apiMock.getSessions).toHaveBeenCalled());
  });

  it("polls the overview on a recurring interval", async () => {
    // The overview hook is wired to setInterval(loadOverview, 5000).  Use
    // fake timers ONLY here so other tests can rely on real microtask
    // ordering for waitFor.
    vi.useFakeTimers({ shouldAdvanceTime: true });
    render(
      <RouterWrapper>
        <SessionsPage />
      </RouterWrapper>,
    );
    await vi.waitFor(() => expect(apiMock.getStatus).toHaveBeenCalled());
    const before = apiMock.getStatus.mock.calls.length;
    await vi.advanceTimersByTimeAsync(5000);
    expect(apiMock.getStatus.mock.calls.length).toBeGreaterThan(before);
    vi.useRealTimers();
  });

  it("consumes useSystemActions context without throwing", () => {
    expect(() =>
      render(
        <RouterWrapper>
          <SessionsPage />
        </RouterWrapper>,
      ),
    ).not.toThrow();
  });
});
