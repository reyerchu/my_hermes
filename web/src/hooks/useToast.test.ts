import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { useToast } from "./useToast";

describe("useToast", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("starts with no toast", () => {
    const { result } = renderHook(() => useToast());
    expect(result.current.toast).toBeNull();
  });

  it("showToast displays a success toast", () => {
    const { result } = renderHook(() => useToast());
    act(() => result.current.showToast("saved!", "success"));
    expect(result.current.toast).toEqual({ message: "saved!", type: "success" });
  });

  it("showToast displays an error toast", () => {
    const { result } = renderHook(() => useToast());
    act(() => result.current.showToast("oops", "error"));
    expect(result.current.toast).toEqual({ message: "oops", type: "error" });
  });

  it("auto-dismisses after the default 3000ms", () => {
    const { result } = renderHook(() => useToast());
    act(() => result.current.showToast("temp", "success"));
    expect(result.current.toast).not.toBeNull();
    act(() => {
      vi.advanceTimersByTime(3000);
    });
    expect(result.current.toast).toBeNull();
  });

  it("honours a custom duration argument", () => {
    const { result } = renderHook(() => useToast(500));
    act(() => result.current.showToast("blink", "success"));
    act(() => {
      vi.advanceTimersByTime(499);
    });
    expect(result.current.toast).not.toBeNull();
    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(result.current.toast).toBeNull();
  });

  it("showToast replaces an existing toast", () => {
    const { result } = renderHook(() => useToast());
    act(() => result.current.showToast("first", "success"));
    act(() => result.current.showToast("second", "error"));
    expect(result.current.toast).toEqual({ message: "second", type: "error" });
  });
});
