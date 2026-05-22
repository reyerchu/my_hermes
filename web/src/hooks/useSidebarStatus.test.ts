import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";

const apiMock = vi.hoisted(() => ({
  getStatus: vi.fn(),
}));
vi.mock("@/lib/api", () => ({ api: apiMock }));

import { useSidebarStatus } from "./useSidebarStatus";

describe("useSidebarStatus", () => {
  beforeEach(() => {
    apiMock.getStatus.mockReset();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("returns null initially and api.getStatus is called on mount", async () => {
    apiMock.getStatus.mockResolvedValue({ ok: true, version: "1.0" });
    const { result } = renderHook(() => useSidebarStatus());
    expect(result.current).toBeNull();
    await waitFor(() =>
      expect(apiMock.getStatus).toHaveBeenCalled(),
    );
  });

  it("stores the resolved status value", async () => {
    apiMock.getStatus.mockResolvedValue({ ok: true, version: "1.2.3" });
    const { result } = renderHook(() => useSidebarStatus());
    await waitFor(() =>
      expect(result.current).toMatchObject({ version: "1.2.3" }),
    );
  });

  it("stays null and does not throw when getStatus rejects", async () => {
    apiMock.getStatus.mockRejectedValue(new Error("offline"));
    const { result } = renderHook(() => useSidebarStatus());
    await waitFor(() => expect(apiMock.getStatus).toHaveBeenCalled());
    expect(result.current).toBeNull();
  });

  it("polls on a recurring interval", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    apiMock.getStatus.mockResolvedValue({ ok: true });
    renderHook(() => useSidebarStatus());
    await vi.waitFor(() => expect(apiMock.getStatus).toHaveBeenCalled());
    const before = apiMock.getStatus.mock.calls.length;
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10_000);
    });
    expect(apiMock.getStatus.mock.calls.length).toBeGreaterThan(before);
  });

  it("clears the poll interval on unmount", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    apiMock.getStatus.mockResolvedValue({ ok: true });
    const { unmount } = renderHook(() => useSidebarStatus());
    await vi.waitFor(() => expect(apiMock.getStatus).toHaveBeenCalled());
    unmount();
    apiMock.getStatus.mockClear();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000);
    });
    expect(apiMock.getStatus).not.toHaveBeenCalled();
  });
});
