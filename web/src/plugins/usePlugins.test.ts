import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";

const apiMock = vi.hoisted(() => ({
  getPlugins: vi.fn(),
}));
vi.mock("@/lib/api", () => ({
  api: apiMock,
  HERMES_BASE_PATH: "",
  fetchJSON: vi.fn(),
}));
// registry.ts pulls in DS components — stub them to keep jsdom resolution clean.
vi.mock("@nous-research/ui/ui/components/badge", () => ({ Badge: () => null }));
vi.mock("@nous-research/ui/ui/components/button", () => ({ Button: () => null }));
vi.mock("@nous-research/ui/ui/components/select", () => ({
  Select: () => null, SelectOption: () => null,
}));
vi.mock("@nous-research/ui/ui/components/tabs", () => ({
  Tabs: () => null, TabsList: () => null, TabsTrigger: () => null,
}));

import { usePlugins } from "./usePlugins";
import { exposePluginSDK } from "./registry";

beforeEach(() => {
  apiMock.getPlugins.mockReset();
  delete (window as any).__HERMES_PLUGINS__;
  exposePluginSDK();
  // Wipe any previously-injected plugin <script> / <link> tags so each
  // test starts with a clean document head/body.
  document
    .querySelectorAll("script[data-hermes-plugin], link[href*='dashboard-plugins']")
    .forEach((el) => el.remove());
});

afterEach(() => {
  vi.useRealTimers();
});

describe("usePlugins", () => {
  it("starts in loading state and calls api.getPlugins on mount", async () => {
    apiMock.getPlugins.mockResolvedValue([]);
    const { result } = renderHook(() => usePlugins());
    expect(result.current.loading).toBe(true);
    await waitFor(() => expect(apiMock.getPlugins).toHaveBeenCalled());
  });

  it("exits loading state when the manifest list is empty", async () => {
    apiMock.getPlugins.mockResolvedValue([]);
    const { result } = renderHook(() => usePlugins());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.manifests).toEqual([]);
    expect(result.current.plugins).toEqual([]);
  });

  it("stores manifests returned by the API", async () => {
    const manifests = [
      { name: "kanban", entry: "kanban.js" },
      { name: "achievements", entry: "achievements.js" },
    ];
    apiMock.getPlugins.mockResolvedValue(manifests);
    const { result } = renderHook(() => usePlugins());
    await waitFor(() =>
      expect(result.current.manifests).toEqual(manifests),
    );
  });

  it("injects a <link> tag for each plugin declaring CSS", async () => {
    apiMock.getPlugins.mockResolvedValue([
      { name: "kanban", entry: "kanban.js", css: "kanban.css" },
    ]);
    renderHook(() => usePlugins());
    await waitFor(() => {
      const link = document.querySelector('link[href*="kanban.css"]');
      expect(link).not.toBeNull();
    });
  });

  it("injects a <script> tag for each plugin's JS entry", async () => {
    apiMock.getPlugins.mockResolvedValue([
      { name: "kanban", entry: "kanban.js" },
    ]);
    renderHook(() => usePlugins());
    await waitFor(() => {
      const script = document.querySelector(
        'script[data-hermes-plugin="kanban"]',
      );
      expect(script).not.toBeNull();
    });
  });

  it("attaches the manifest integrity hash to the script tag", async () => {
    apiMock.getPlugins.mockResolvedValue([
      {
        name: "kanban",
        entry: "kanban.js",
        integrity: "sha384-abc",
      },
    ]);
    renderHook(() => usePlugins());
    await waitFor(() => {
      const s = document.querySelector(
        'script[data-hermes-plugin="kanban"]',
      ) as HTMLScriptElement | null;
      expect(s?.integrity).toBe("sha384-abc");
      expect(s?.crossOrigin).toBe("anonymous");
    });
  });

  it("resolves a plugin to a component once register() runs", async () => {
    apiMock.getPlugins.mockResolvedValue([
      { name: "kanban", entry: "kanban.js" },
    ]);
    const { result } = renderHook(() => usePlugins());
    await waitFor(() => expect(result.current.manifests.length).toBe(1));

    function KanbanPlugin() {
      return null;
    }
    await act(async () => {
      (window as any).__HERMES_PLUGINS__.register("kanban", KanbanPlugin);
    });
    await waitFor(() => expect(result.current.plugins.length).toBe(1));
    expect(result.current.plugins[0].manifest.name).toBe("kanban");
    expect(result.current.plugins[0].component).toBe(KanbanPlugin);
  });

  it("exits loading once all manifests have registered", async () => {
    apiMock.getPlugins.mockResolvedValue([
      { name: "kanban", entry: "kanban.js" },
    ]);
    const { result } = renderHook(() => usePlugins());
    await waitFor(() => expect(result.current.manifests.length).toBe(1));
    function P() {
      return null;
    }
    await act(async () => {
      (window as any).__HERMES_PLUGINS__.register("kanban", P);
    });
    await waitFor(() => expect(result.current.loading).toBe(false));
  });

  it("recovers gracefully when api.getPlugins rejects", async () => {
    apiMock.getPlugins.mockImplementation(
      () =>
        new Promise((_, reject) =>
          setTimeout(() => reject(new Error("offline")), 0),
        ),
    );
    const { result } = renderHook(() => usePlugins());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.manifests).toEqual([]);
  });
});
