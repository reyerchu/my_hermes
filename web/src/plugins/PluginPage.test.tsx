import { describe, it, expect, vi, afterEach } from "vitest";
import { render, cleanup } from "@testing-library/react";

// registry.ts re-exports DS components onto window.__HERMES_PLUGIN_SDK__,
// so importing the registry pulls in @nous-research/ui transitively.  Stub
// them to keep jsdom happy.
vi.mock("@nous-research/ui/ui/components/badge", () => ({ Badge: () => null }));
vi.mock("@nous-research/ui/ui/components/button", () => ({ Button: () => null }));
vi.mock("@nous-research/ui/ui/components/select", () => ({
  Select: () => null, SelectOption: () => null,
}));
vi.mock("@nous-research/ui/ui/components/tabs", () => ({
  Tabs: () => null, TabsList: () => null, TabsTrigger: () => null,
}));
vi.mock("@nous-research/ui/ui/components/spinner", () => ({
  Spinner: () => <div data-testid="spinner" />,
}));
// registry.ts also imports api / fetchJSON to expose on the SDK — provide
// inert stand-ins.
vi.mock("@/lib/api", () => ({ api: {}, fetchJSON: () => {}, HERMES_BASE_PATH: "" }));

import { exposePluginSDK, setPluginLoadError } from "./registry";
vi.mock("@/i18n", () => ({
  useI18n: () => ({
    t: {
      common: {
        loading: "Loading…",
        pluginLoadFailed: "Plugin failed to load",
        pluginNotRegistered: "Plugin did not register",
      },
    },
  }),
}));

import { PluginPage } from "./PluginPage";

afterEach(() => {
  cleanup();
  // Reset the SDK registry so test order doesn't matter.
  delete (window as any).__HERMES_PLUGINS__;
  exposePluginSDK();
});

describe("PluginPage", () => {
  it("shows a spinner while the plugin has not registered and no error", () => {
    const { getByTestId } = render(<PluginPage name="missing" />);
    expect(getByTestId("spinner")).toBeTruthy();
  });

  it("renders the plugin component once register() runs", () => {
    function Foo() {
      return <div data-testid="plugin-foo">FOO</div>;
    }
    (window as any).__HERMES_PLUGINS__.register("foo", Foo);
    const { getByTestId } = render(<PluginPage name="foo" />);
    expect(getByTestId("plugin-foo")).toBeTruthy();
  });

  it("renders the LOAD_FAILED message when the bundle failed to fetch", () => {
    setPluginLoadError("crashed", "LOAD_FAILED");
    const { container } = render(<PluginPage name="crashed" />);
    expect(container.textContent).toContain("Plugin failed to load");
  });

  it("renders the NO_REGISTER message when the bundle loaded but didn't register", () => {
    setPluginLoadError("silent", "NO_REGISTER");
    const { container } = render(<PluginPage name="silent" />);
    expect(container.textContent).toContain("Plugin did not register");
  });

  it("falls through to the raw error code for an unknown error", () => {
    setPluginLoadError("weird", "SOMETHING_ELSE");
    const { container } = render(<PluginPage name="weird" />);
    expect(container.textContent).toContain("SOMETHING_ELSE");
  });

  it("prefers the component when both register() and an error exist", () => {
    setPluginLoadError("dual", "LOAD_FAILED");
    function DualPlugin() {
      return <div data-testid="dual">DUAL</div>;
    }
    (window as any).__HERMES_PLUGINS__.register("dual", DualPlugin);
    const { getByTestId } = render(<PluginPage name="dual" />);
    expect(getByTestId("dual")).toBeTruthy();
  });
});
