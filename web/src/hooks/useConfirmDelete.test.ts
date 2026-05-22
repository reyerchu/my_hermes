import { describe, it, expect, vi } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";
import { useConfirmDelete } from "./useConfirmDelete";

function setup(onDelete: (id: string) => Promise<void> = async () => {}) {
  return renderHook(() => useConfirmDelete<string>({ onDelete }));
}

describe("useConfirmDelete", () => {
  it("starts closed", () => {
    const { result } = setup();
    expect(result.current.isOpen).toBe(false);
    expect(result.current.pendingId).toBeNull();
    expect(result.current.isDeleting).toBe(false);
  });

  it("requestDelete opens the dialog and records id", () => {
    const { result } = setup();
    act(() => result.current.requestDelete("abc"));
    expect(result.current.isOpen).toBe(true);
    expect(result.current.pendingId).toBe("abc");
  });

  it("cancel closes when not currently deleting", () => {
    const { result } = setup();
    act(() => result.current.requestDelete("abc"));
    act(() => result.current.cancel());
    expect(result.current.isOpen).toBe(false);
    expect(result.current.pendingId).toBeNull();
  });

  it("confirm invokes onDelete with the pending id and then closes", async () => {
    const onDelete = vi.fn().mockResolvedValue(undefined);
    const { result } = setup(onDelete);
    act(() => result.current.requestDelete("zzz"));
    await act(async () => {
      await result.current.confirm();
    });
    expect(onDelete).toHaveBeenCalledWith("zzz");
    expect(result.current.isOpen).toBe(false);
    expect(result.current.isDeleting).toBe(false);
  });

  it("confirm is a no-op when nothing is pending", async () => {
    const onDelete = vi.fn();
    const { result } = setup(onDelete);
    await act(async () => {
      await result.current.confirm();
    });
    expect(onDelete).not.toHaveBeenCalled();
  });

  it("keeps dialog open if onDelete throws", async () => {
    const onDelete = vi.fn().mockRejectedValue(new Error("boom"));
    const { result } = setup(onDelete);
    act(() => result.current.requestDelete("oops"));
    await act(async () => {
      await result.current.confirm();
    });
    expect(result.current.isOpen).toBe(true);
    expect(result.current.pendingId).toBe("oops");
    expect(result.current.isDeleting).toBe(false);
  });

  it("flips isDeleting to true while onDelete is in flight", async () => {
    let resolveFn!: () => void;
    const onDelete = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          resolveFn = resolve;
        }),
    );
    const { result } = setup(onDelete);
    act(() => result.current.requestDelete("slow"));
    let confirmPromise!: Promise<void>;
    act(() => {
      confirmPromise = result.current.confirm();
    });
    await waitFor(() => expect(result.current.isDeleting).toBe(true));
    act(() => resolveFn());
    await act(async () => {
      await confirmPromise;
    });
    expect(result.current.isDeleting).toBe(false);
  });
});
