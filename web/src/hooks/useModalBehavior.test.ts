import { describe, it, expect, vi, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useModalBehavior } from "./useModalBehavior";

afterEach(() => {
  document.body.style.overflow = "";
});

describe("useModalBehavior", () => {
  it("returns a ref object the caller can attach to a container", () => {
    const { result } = renderHook(() =>
      useModalBehavior({ open: false, onClose: () => {} }),
    );
    expect(result.current).toHaveProperty("current");
  });

  it("does NOT lock body scroll while closed", () => {
    document.body.style.overflow = "auto";
    renderHook(() => useModalBehavior({ open: false, onClose: () => {} }));
    expect(document.body.style.overflow).toBe("auto");
  });

  it("locks body scroll while open", () => {
    document.body.style.overflow = "auto";
    renderHook(() => useModalBehavior({ open: true, onClose: () => {} }));
    expect(document.body.style.overflow).toBe("hidden");
  });

  it("restores body scroll when toggled back to closed", () => {
    document.body.style.overflow = "auto";
    const { rerender } = renderHook(
      ({ open }) => useModalBehavior({ open, onClose: () => {} }),
      { initialProps: { open: true } },
    );
    expect(document.body.style.overflow).toBe("hidden");
    rerender({ open: false });
    expect(document.body.style.overflow).toBe("auto");
  });

  it("Escape key triggers onClose when open", () => {
    const onClose = vi.fn();
    renderHook(() => useModalBehavior({ open: true, onClose }));
    act(() => {
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    });
    expect(onClose).toHaveBeenCalled();
  });

  it("Escape key does NOT trigger onClose when closed", () => {
    const onClose = vi.fn();
    renderHook(() => useModalBehavior({ open: false, onClose }));
    act(() => {
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    });
    expect(onClose).not.toHaveBeenCalled();
  });

  it("other keys don't trigger onClose", () => {
    const onClose = vi.fn();
    renderHook(() => useModalBehavior({ open: true, onClose }));
    act(() => {
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter" }));
    });
    expect(onClose).not.toHaveBeenCalled();
  });

  it("removes the keydown listener on unmount", () => {
    const onClose = vi.fn();
    const { unmount } = renderHook(() =>
      useModalBehavior({ open: true, onClose }),
    );
    unmount();
    act(() => {
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    });
    expect(onClose).not.toHaveBeenCalled();
  });
});
