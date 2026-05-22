/**
 * App.tsx smoke tests.  The component is a route shell that imports
 * every page plus several design-language components.  We stub the
 * heavy boundary (pages, DS components, plugin runtime) so the test
 * exercises only the routing + nav rendering that App owns.
 */
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, cleanup } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { makeTranslationStub } from "@/test-helpers";

// Stub every page so we don't transitively pull their dependencies.
vi.mock("@/pages/ChatPage", () => ({ default: () => <div data-testid="page-chat" /> }));
vi.mock("@/pages/SessionsPage", () => ({ default: () => <div data-testid="page-sessions" /> }));
vi.mock("@/pages/AnalyticsPage", () => ({ default: () => <div data-testid="page-analytics" /> }));
vi.mock("@/pages/ConfigPage", () => ({ default: () => <div data-testid="page-config" /> }));
vi.mock("@/pages/CronPage", () => ({ default: () => <div data-testid="page-cron" /> }));
vi.mock("@/pages/DocsPage", () => ({ default: () => <div data-testid="page-docs" /> }));
vi.mock("@/pages/EnvPage", () => ({ default: () => <div data-testid="page-env" /> }));
vi.mock("@/pages/LogsPage", () => ({ default: () => <div data-testid="page-logs" /> }));
vi.mock("@/pages/ModelsPage", () => ({ default: () => <div data-testid="page-models" /> }));
vi.mock("@/pages/PluginsPage", () => ({ default: () => <div data-testid="page-plugins" /> }));
vi.mock("@/pages/ProfilesPage", () => ({ default: () => <div data-testid="page-profiles" /> }));
vi.mock("@/pages/SkillsPage", () => ({ default: () => <div data-testid="page-skills" /> }));

// usePlugins + plugin slots are inert for the smoke test.
vi.mock("@/plugins/usePlugins", () => ({
  usePlugins: () => ({ plugins: [], manifests: [], loading: false }),
}));
vi.mock("@/plugins", () => ({
  PluginSlot: () => null,
  PluginPage: () => null,
  KNOWN_SLOT_NAMES: [],
  registerSlot: () => {},
  getSlotEntries: () => [],
  onSlotRegistered: () => () => {},
  unregisterPluginSlots: () => {},
  usePlugins: () => ({ plugins: [], manifests: [], loading: false }),
  exposePluginSDK: () => {},
  getPluginComponent: () => undefined,
  onPluginRegistered: () => () => {},
  getRegisteredCount: () => 0,
}));
vi.mock("@/components/Backdrop", () => ({ Backdrop: () => null }));
vi.mock("@/components/SidebarFooter", () => ({ SidebarFooter: () => null }));
vi.mock("@/components/SidebarStatusStrip", () => ({
  SidebarStatusStrip: () => null,
}));
vi.mock("@/components/LanguageSwitcher", () => ({
  LanguageSwitcher: () => null,
}));
vi.mock("@/components/ThemeSwitcher", () => ({ ThemeSwitcher: () => null }));
vi.mock("@/contexts/PageHeaderProvider", () => ({
  PageHeaderProvider: ({ children }: any) => <>{children}</>,
}));
vi.mock("@/contexts/useSystemActions", () => ({
  useSystemActions: () => ({
    activeAction: null,
    actionStatus: null,
    dismissLog: () => {},
    isBusy: false,
    isRunning: false,
    pendingAction: null,
    runAction: () => {},
  }),
}));
vi.mock("@/i18n", () => ({ useI18n: () => ({ t: makeTranslationStub() }) }));
vi.mock("@nous-research/ui/ui/components/button", () => ({
  Button: ({ children, onClick }: any) => (
    <button onClick={onClick}>{children}</button>
  ),
}));
vi.mock("@nous-research/ui/ui/components/list-item", () => ({
  ListItem: ({ children, onClick }: any) => (
    <div role="listitem" onClick={onClick}>{children}</div>
  ),
}));
vi.mock("@nous-research/ui/ui/components/selection-switcher", () => ({
  SelectionSwitcher: () => null,
}));
vi.mock("@nous-research/ui/ui/components/spinner", () => ({
  Spinner: () => null,
}));
vi.mock("@/components/NouiTypography", () => ({
  Typography: ({ children }: any) => <span>{children}</span>,
}));

// jsdom lacks matchMedia + ResizeObserver; App's responsive helpers poke
// at both during initial render.
if (!window.matchMedia) {
  window.matchMedia = ((q: string) => ({
    matches: false,
    media: q,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia;
}
if (typeof window.ResizeObserver === "undefined") {
  class ROStub {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  (window as any).ResizeObserver = ROStub;
}

import App from "./App";

afterEach(() => cleanup());

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

describe("App routing", () => {
  it("renders the sessions page at /", () => {
    const { getByTestId } = renderAt("/");
    expect(getByTestId("page-sessions")).toBeTruthy();
  });

  it("/chat does not crash (chat route is conditional on embedded mode)", () => {
    // ChatPage is mounted persistently outside <Routes> only when the
    // dashboard runs in embedded-chat mode, so a smoke test asserts that
    // visiting /chat at minimum does not throw under jsdom.
    expect(() => renderAt("/chat")).not.toThrow();
  });

  it("/analytics renders AnalyticsPage", () => {
    expect(renderAt("/analytics").getByTestId("page-analytics")).toBeTruthy();
  });

  it("/config renders ConfigPage", () => {
    expect(renderAt("/config").getByTestId("page-config")).toBeTruthy();
  });

  it("/cron renders CronPage", () => {
    expect(renderAt("/cron").getByTestId("page-cron")).toBeTruthy();
  });

  it("/docs renders DocsPage", () => {
    expect(renderAt("/docs").getByTestId("page-docs")).toBeTruthy();
  });

  it("/env renders EnvPage", () => {
    expect(renderAt("/env").getByTestId("page-env")).toBeTruthy();
  });

  it("/logs renders LogsPage", () => {
    expect(renderAt("/logs").getByTestId("page-logs")).toBeTruthy();
  });

  it("/models renders ModelsPage", () => {
    expect(renderAt("/models").getByTestId("page-models")).toBeTruthy();
  });

  it("/plugins renders PluginsPage", () => {
    expect(renderAt("/plugins").getByTestId("page-plugins")).toBeTruthy();
  });

  it("/profiles renders ProfilesPage", () => {
    expect(renderAt("/profiles").getByTestId("page-profiles")).toBeTruthy();
  });

  it("/skills renders SkillsPage", () => {
    expect(renderAt("/skills").getByTestId("page-skills")).toBeTruthy();
  });

  it("renders without crashing for an unknown path (fallback / not-found)", () => {
    expect(() => renderAt("/totally-unknown")).not.toThrow();
  });
});
