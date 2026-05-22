import { describe, it, expect, vi, beforeEach } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";
import { useSystemActions } from "./useSystemActions";
import { SystemActionsProvider } from "./SystemActions";

// We mock api and i18n: SystemActionsProvider only depends on these two
// boundaries so this keeps the tests fast and deterministic.
//
// vi.mock factory is hoisted; use vi.hoisted so the mock object is created
// before the factory runs.
const apiMock = vi.hoisted(() => ({
  restartGateway: vi.fn(),
  updateHermes: vi.fn(),
  getActionStatus: vi.fn(),
}));
vi.mock("@/lib/api", () => ({
  api: apiMock,
}));
vi.mock("@/i18n", () => ({
  useI18n: () => ({
    t: {
      status: {
        actionFinished: "Action finished",
        actionFailed: "Action failed",
      },
    },
  }),
}));

describe("useSystemActions (outside provider)", () => {
  it("throws a helpful error when used without provider", () => {
    expect(() => renderHook(() => useSystemActions())).toThrow(
      /must be used within a SystemActionsProvider/,
    );
  });
});

function wrapper({ children }: { children: React.ReactNode }) {
  return <SystemActionsProvider>{children}</SystemActionsProvider>;
}

describe("SystemActionsProvider", () => {
  beforeEach(() => {
    apiMock.restartGateway.mockReset();
    apiMock.updateHermes.mockReset();
    apiMock.getActionStatus.mockReset();
  });

  it("starts idle", () => {
    const { result } = renderHook(() => useSystemActions(), { wrapper });
    expect(result.current.activeAction).toBeNull();
    expect(result.current.actionStatus).toBeNull();
    expect(result.current.pendingAction).toBeNull();
    expect(result.current.isBusy).toBe(false);
    expect(result.current.isRunning).toBe(false);
  });

  it("runAction('restart') calls the restart endpoint and activates polling", async () => {
    apiMock.restartGateway.mockResolvedValue(undefined);
    apiMock.getActionStatus.mockResolvedValue({ running: true, exit_code: null });
    const { result } = renderHook(() => useSystemActions(), { wrapper });
    await act(async () => {
      await result.current.runAction("restart");
    });
    expect(apiMock.restartGateway).toHaveBeenCalledOnce();
    expect(result.current.activeAction).toBe("restart");
    expect(result.current.isBusy).toBe(true);
  });

  it("runAction('update') calls updateHermes", async () => {
    apiMock.updateHermes.mockResolvedValue(undefined);
    apiMock.getActionStatus.mockResolvedValue({ running: true, exit_code: null });
    const { result } = renderHook(() => useSystemActions(), { wrapper });
    await act(async () => {
      await result.current.runAction("update");
    });
    expect(apiMock.updateHermes).toHaveBeenCalledOnce();
    expect(result.current.activeAction).toBe("update");
  });

  it("runAction error leaves activeAction null", async () => {
    apiMock.restartGateway.mockRejectedValue(new Error("network"));
    const { result } = renderHook(() => useSystemActions(), { wrapper });
    await act(async () => {
      await result.current.runAction("restart");
    });
    expect(result.current.activeAction).toBeNull();
    expect(result.current.pendingAction).toBeNull();
  });

  it("dismissLog clears active action and status", async () => {
    apiMock.restartGateway.mockResolvedValue(undefined);
    apiMock.getActionStatus.mockResolvedValue({ running: false, exit_code: 0 });
    const { result } = renderHook(() => useSystemActions(), { wrapper });
    await act(async () => {
      await result.current.runAction("restart");
    });
    // Wait for poll to finish.
    await waitFor(() => expect(result.current.actionStatus).not.toBeNull());
    act(() => result.current.dismissLog());
    expect(result.current.activeAction).toBeNull();
    expect(result.current.actionStatus).toBeNull();
  });
});
