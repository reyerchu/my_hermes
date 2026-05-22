import { describe, it, expect, vi, afterEach } from "vitest";
import { render, cleanup } from "@testing-library/react";

// useGpuTier from @nous-research/ui pulls in three/webgl probes that fail
// in jsdom — stub it.  Backdrop renders the noise layer only when tier > 0,
// so we can flip between the two branches by changing the mock return.
const gpuTier = vi.hoisted(() => ({ value: 0 }));
vi.mock("@nous-research/ui/hooks/use-gpu-tier", () => ({
  useGpuTier: () => gpuTier.value,
}));

import { Backdrop } from "./Backdrop";

afterEach(() => {
  cleanup();
  gpuTier.value = 0;
});

describe("Backdrop", () => {
  it("renders 3 background layers when GPU tier is 0", () => {
    const { container } = render(<Backdrop />);
    // The first three layers (deep canvas, filler bg, warm vignette) are
    // always present; the noise layer is gated on tier > 0.
    expect(container.querySelectorAll("[aria-hidden]").length).toBeGreaterThanOrEqual(3);
  });

  it("includes the noise layer only when GPU tier > 0", () => {
    gpuTier.value = 0;
    const { container, rerender } = render(<Backdrop />);
    const noTierLayers = container.querySelectorAll("[aria-hidden]").length;
    gpuTier.value = 2;
    rerender(<Backdrop />);
    const withTierLayers = container.querySelectorAll("[aria-hidden]").length;
    expect(withTierLayers).toBeGreaterThan(noTierLayers);
  });

  it("renders the filler-bg image once", () => {
    const { container } = render(<Backdrop />);
    const img = container.querySelector("img");
    expect(img).not.toBeNull();
    expect(img!.getAttribute("src")).toContain("filler-bg");
  });

  it("filler-bg image has empty alt for decorative usage", () => {
    const { container } = render(<Backdrop />);
    expect(container.querySelector("img")!.getAttribute("alt")).toBe("");
  });

  it("every layer is aria-hidden + pointer-events-none", () => {
    const { container } = render(<Backdrop />);
    container.querySelectorAll("[aria-hidden]").forEach((el) => {
      expect(el.className).toContain("pointer-events-none");
    });
  });
});
