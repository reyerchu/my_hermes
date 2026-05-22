import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";

vi.mock("@/hooks/useSidebarStatus", () => ({
  useSidebarStatus: () => ({ version: "9.9.9", ok: true }),
}));
vi.mock("@/i18n", () => ({
  useI18n: () => ({
    t: { app: { website: "nousresearch.com", footer: { org: "Nous Research" } } },
  }),
}));

import { SidebarFooter } from "./SidebarFooter";

describe("SidebarFooter", () => {
  it("renders the version label from useSidebarStatus", () => {
    const { container } = render(<SidebarFooter />);
    expect(container.textContent).toContain("v9.9.9");
  });

  it("renders an external link to nousresearch.com with target=_blank", () => {
    const { container } = render(<SidebarFooter />);
    const link = container.querySelector("a");
    expect(link).not.toBeNull();
    expect(link!.href).toContain("nousresearch.com");
    expect(link!.target).toBe("_blank");
    expect(link!.rel).toContain("noopener");
  });
});

describe("SidebarFooter with no status loaded", () => {
  it("falls back to em-dash when version is missing", async () => {
    // Re-import after redirecting the mock to return null.
    vi.resetModules();
    vi.doMock("@/hooks/useSidebarStatus", () => ({
      useSidebarStatus: () => null,
    }));
    vi.doMock("@/i18n", () => ({
      useI18n: () => ({
        t: { app: { website: "nousresearch.com", footer: { org: "Nous" } } },
      }),
    }));
    const { SidebarFooter: Fresh } = await import("./SidebarFooter");
    const { container } = render(<Fresh />);
    expect(container.textContent).toContain("—");
  });
});
