import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, cleanup } from "@testing-library/react";
import { RouterWrapper, stubT, makePageHeaderStub } from "@/test-helpers";

const headerStub = vi.hoisted(() => ({
  setTitle: vi.fn(),
  setAfterTitle: vi.fn(),
  setEnd: vi.fn(),
}));

vi.mock("@/i18n", () => ({
  useI18n: () => ({ t: {
    app: {
      webUi: "Hermes Web",
      openDocumentation: "Open Documentation",
      statusOverview: "Status",
      activeSessionsLabel: "Active",
      gatewayStatusLabel: "Gateway",
      nav: {
        chat: "Chat", sessions: "Sessions", analytics: "Analytics",
        models: "Models", logs: "Logs", cron: "Cron", skills: "Skills",
        plugins: "Plugins", profiles: "Profiles", config: "Config",
        keys: "Env Keys", documentation: "Docs",
      },
    },
    common: { cancel: "Cancel", delete: "Delete", save: "Save",
              edit: "Edit", add: "Add", close: "Close", confirm: "Confirm" },
    status: { actionFinished: "Action finished", actionFailed: "Action failed" },
  } }),
}));
vi.mock("@/contexts/usePageHeader", () => ({
  usePageHeader: () => headerStub,
}));
vi.mock("@/plugins", () => ({
  PluginSlot: ({ name }: { name: string }) => <div data-testid={`slot-${name}`} />,
}));

import DocsPage, { HERMES_DOCS_URL } from "./DocsPage";

describe("DocsPage", () => {
  beforeEach(() => {
    headerStub.setEnd.mockClear();
    headerStub.setTitle.mockClear();
    headerStub.setAfterTitle.mockClear();
  });
  afterEach(() => {
    cleanup();
  });

  it("renders the docs iframe pointing at the official docs URL", () => {
    const { container } = render(
      <RouterWrapper>
        <DocsPage />
      </RouterWrapper>,
    );
    const iframe = container.querySelector("iframe");
    expect(iframe).not.toBeNull();
    expect(iframe!.getAttribute("src")).toBe(HERMES_DOCS_URL);
  });

  it("iframe has a meaningful accessible title from i18n", () => {
    const { container } = render(
      <RouterWrapper>
        <DocsPage />
      </RouterWrapper>,
    );
    expect(container.querySelector("iframe")!.getAttribute("title")).toBe("Docs");
  });

  it("renders the plugin slots so plugins can extend the docs page", () => {
    const { getByTestId } = render(
      <RouterWrapper>
        <DocsPage />
      </RouterWrapper>,
    );
    expect(getByTestId("slot-docs:top")).toBeTruthy();
    expect(getByTestId("slot-docs:bottom")).toBeTruthy();
  });

  it("registers a header-end action with the page-header context on mount", () => {
    render(
      <RouterWrapper>
        <DocsPage />
      </RouterWrapper>,
    );
    expect(headerStub.setEnd).toHaveBeenCalled();
    // The first call is the registration; the second (on unmount) clears it.
    const firstCallArg = headerStub.setEnd.mock.calls[0][0];
    expect(firstCallArg).not.toBeNull();
  });

  it("clears the header-end action on unmount", () => {
    const { unmount } = render(
      <RouterWrapper>
        <DocsPage />
      </RouterWrapper>,
    );
    headerStub.setEnd.mockClear();
    unmount();
    // The cleanup ran with null.
    expect(headerStub.setEnd).toHaveBeenCalledWith(null);
  });

  it("docs iframe enforces a light color scheme for the embedded docs", () => {
    const { container } = render(
      <RouterWrapper>
        <DocsPage />
      </RouterWrapper>,
    );
    const cn = container.querySelector("iframe")!.getAttribute("class") ?? "";
    expect(cn).toMatch(/color-scheme:light/);
  });
});

