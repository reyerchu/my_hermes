import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { act, render, renderHook, waitFor } from "@testing-library/react";

const apiMock = vi.hoisted(() => ({
  getThemes: vi.fn(),
  setTheme: vi.fn().mockResolvedValue({}),
}));
vi.mock("@/lib/api", () => ({ api: apiMock }));

// jsdom lacks CSS.escape — provide a minimal polyfill so font-URL injection
// inside applyTheme does not throw when setTheme is called in a test.
if (typeof (globalThis as any).CSS === "undefined") {
  (globalThis as any).CSS = {};
}
if (typeof (globalThis as any).CSS.escape !== "function") {
  (globalThis as any).CSS.escape = (s: string) =>
    s.replace(/[^a-zA-Z0-9_-]/g, "\\$&");
}

import { ThemeProvider, useTheme } from "./context";
import { BUILTIN_THEMES, defaultTheme } from "./presets";

function wrapper({ children }: { children: React.ReactNode }) {
  return <ThemeProvider>{children}</ThemeProvider>;
}

beforeEach(() => {
  localStorage.clear();
  apiMock.getThemes.mockResolvedValue({ themes: [] });
  apiMock.setTheme.mockResolvedValue({});
});

afterEach(() => {
  localStorage.clear();
});

describe("ThemeProvider initial state", () => {
  it("defaults to 'default' when localStorage is empty", () => {
    const { result } = renderHook(() => useTheme(), { wrapper });
    expect(result.current.themeName).toBe("default");
  });

  it("loads the persisted theme name from localStorage", () => {
    localStorage.setItem("hermes-dashboard-theme", "ember");
    const { result } = renderHook(() => useTheme(), { wrapper });
    expect(result.current.themeName).toBe("ember");
  });

  it("populates availableThemes from BUILTIN_THEMES initially", () => {
    const { result } = renderHook(() => useTheme(), { wrapper });
    const names = result.current.availableThemes.map((t) => t.name);
    for (const builtin of Object.values(BUILTIN_THEMES)) {
      expect(names).toContain(builtin.name);
    }
  });
});

describe("setTheme", () => {
  it("updates the active theme name", () => {
    const { result } = renderHook(() => useTheme(), { wrapper });
    act(() => result.current.setTheme("ember"));
    expect(result.current.themeName).toBe("ember");
  });

  it("persists the chosen theme to localStorage", () => {
    const { result } = renderHook(() => useTheme(), { wrapper });
    act(() => result.current.setTheme("midnight"));
    expect(localStorage.getItem("hermes-dashboard-theme")).toBe("midnight");
  });
});

describe("API integration", () => {
  it("calls api.getThemes once on mount", async () => {
    renderHook(() => useTheme(), { wrapper });
    await waitFor(() => expect(apiMock.getThemes).toHaveBeenCalled());
  });

  it("merges server-provided themes into availableThemes", async () => {
    apiMock.getThemes.mockResolvedValue({
      themes: [
        { name: "default", label: "Default", description: "" },
        { name: "user-foo", label: "User Foo", description: "" },
      ],
    });
    const { result } = renderHook(() => useTheme(), { wrapper });
    await waitFor(() => {
      const names = result.current.availableThemes.map((t) => t.name);
      expect(names).toContain("user-foo");
    });
  });

  it("recovers gracefully when getThemes rejects", async () => {
    apiMock.getThemes.mockImplementation(
      () => new Promise((_, reject) => setTimeout(() => reject(new Error("x")), 0)),
    );
    expect(() => renderHook(() => useTheme(), { wrapper })).not.toThrow();
    await waitFor(() => expect(apiMock.getThemes).toHaveBeenCalled());
  });
});

describe("useTheme outside provider", () => {
  it("returns the default theme without throwing", () => {
    const { result } = renderHook(() => useTheme());
    expect(result.current.themeName).toBe("default");
    expect(result.current.theme).toEqual(defaultTheme);
  });
});

describe("ThemeProvider rendering", () => {
  it("renders children", () => {
    const { container } = render(
      <ThemeProvider>
        <span data-testid="x">x</span>
      </ThemeProvider>,
    );
    expect(container.querySelector("[data-testid='x']")).not.toBeNull();
  });
});
