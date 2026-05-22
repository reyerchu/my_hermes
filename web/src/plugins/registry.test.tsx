/**
 * Coverage for the plugin component registry.  Like slots.ts this module
 * owns global state (Map<name, Component>), so each test resets that
 * state via window.__HERMES_PLUGINS__ helpers.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";

// registry.ts imports @nous-research/ui components purely so they can be
// re-exported on the global SDK; stub them to avoid pulling in their
// canvas/webgl peer deps under jsdom.
vi.mock("@nous-research/ui/ui/components/badge", () => ({ Badge: () => null }));
vi.mock("@nous-research/ui/ui/components/button", () => ({ Button: () => null }));
vi.mock("@nous-research/ui/ui/components/select", () => ({
  Select: () => null, SelectOption: () => null,
}));
vi.mock("@nous-research/ui/ui/components/tabs", () => ({
  Tabs: () => null, TabsList: () => null, TabsTrigger: () => null,
}));

import {
  getPluginComponent,
  getPluginLoadError,
  getRegisteredCount,
  notifyPluginRegistry,
  onPluginRegistered,
  setPluginLoadError,
  exposePluginSDK,
} from "./registry";

function DummyPlugin() {
  return null;
}

// exposePluginSDK plants window.__HERMES_PLUGINS__ for plugin bundles to call.
beforeEach(() => {
  // Clear state from previous tests by removing the SDK and re-installing.
  delete (window as any).__HERMES_PLUGINS__;
  exposePluginSDK();
});

describe("getRegisteredCount", () => {
  it("returns 0 when nothing is registered", () => {
    expect(getRegisteredCount()).toBe(0);
  });

  it("counts each unique plugin name once", () => {
    (window as any).__HERMES_PLUGINS__.register("a", DummyPlugin);
    (window as any).__HERMES_PLUGINS__.register("b", DummyPlugin);
    expect(getRegisteredCount()).toBe(2);
  });

  it("re-registering an existing name does not double-count", () => {
    // The registry is module-scoped state shared across tests; capture the
    // baseline before/after a duplicate register to assert "no increase"
    // without depending on absolute counts.
    (window as any).__HERMES_PLUGINS__.register("dup-name", DummyPlugin);
    const before = getRegisteredCount();
    (window as any).__HERMES_PLUGINS__.register("dup-name", DummyPlugin);
    expect(getRegisteredCount()).toBe(before);
  });
});

describe("getPluginComponent", () => {
  it("returns undefined for an unknown plugin", () => {
    expect(getPluginComponent("nope")).toBeUndefined();
  });

  it("returns the component the plugin registered", () => {
    (window as any).__HERMES_PLUGINS__.register("kanban", DummyPlugin);
    expect(getPluginComponent("kanban")).toBe(DummyPlugin);
  });
});

describe("onPluginRegistered subscription", () => {
  it("fires when a plugin registers", () => {
    const listener = vi.fn();
    const unsub = onPluginRegistered(listener);
    (window as any).__HERMES_PLUGINS__.register("a", DummyPlugin);
    expect(listener).toHaveBeenCalled();
    unsub();
  });

  it("fires on notifyPluginRegistry()", () => {
    const listener = vi.fn();
    const unsub = onPluginRegistered(listener);
    notifyPluginRegistry();
    expect(listener).toHaveBeenCalled();
    unsub();
  });

  it("stops firing after unsubscribe", () => {
    const listener = vi.fn();
    const unsub = onPluginRegistered(listener);
    unsub();
    (window as any).__HERMES_PLUGINS__.register("a", DummyPlugin);
    expect(listener).not.toHaveBeenCalled();
  });

  it("a throwing listener does not crash the notify pass", () => {
    const good = vi.fn();
    onPluginRegistered(() => {
      throw new Error("bad");
    });
    onPluginRegistered(good);
    (window as any).__HERMES_PLUGINS__.register("a", DummyPlugin);
    expect(good).toHaveBeenCalled();
  });
});

describe("plugin load errors", () => {
  it("starts with no error for any plugin", () => {
    expect(getPluginLoadError("never-loaded")).toBeUndefined();
  });

  it("setPluginLoadError stores and exposes the error message", () => {
    setPluginLoadError("kanban", "failed to fetch bundle");
    expect(getPluginLoadError("kanban")).toBe("failed to fetch bundle");
  });

  it("a successful register clears any prior error for that plugin", () => {
    setPluginLoadError("kanban", "boom");
    (window as any).__HERMES_PLUGINS__.register("kanban", DummyPlugin);
    expect(getPluginLoadError("kanban")).toBeUndefined();
  });

  it("setPluginLoadError notifies subscribers", () => {
    const listener = vi.fn();
    const unsub = onPluginRegistered(listener);
    setPluginLoadError("kanban", "fail");
    expect(listener).toHaveBeenCalled();
    unsub();
  });
});

describe("exposePluginSDK", () => {
  it("installs __HERMES_PLUGINS__ with register + registerSlot", () => {
    const sdk = (window as any).__HERMES_PLUGINS__;
    expect(sdk).toBeDefined();
    expect(typeof sdk.register).toBe("function");
    expect(typeof sdk.registerSlot).toBe("function");
  });

  it("installs __HERMES_PLUGIN_SDK__ exposing React for plugin dedupe", () => {
    const sdk = (window as any).__HERMES_PLUGIN_SDK__;
    expect(sdk).toBeDefined();
    expect(sdk.React).toBeDefined();
    expect(typeof sdk.hooks?.useState).toBe("function");
  });

  it("calling exposePluginSDK again keeps the register API live", () => {
    exposePluginSDK();
    const sdk = (window as any).__HERMES_PLUGINS__;
    expect(typeof sdk.register).toBe("function");
  });
});
