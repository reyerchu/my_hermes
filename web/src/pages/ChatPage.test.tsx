import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, cleanup } from "@testing-library/react";
import { RouterWrapper, makeTranslationStub } from "@/test-helpers";

// ChatPage embeds an @xterm/xterm Terminal with WebGL + Unicode 11 addons,
// then opens a WebSocket to /api/pty.  Both behaviours blow up in jsdom
// because there's no real canvas / WebGL / WebSocket, so the test stubs
// every external behaviour and asserts only "this page renders" + the
// few side effects we own (resume rewrite via api.getSessionLatestDescendant
// and header chrome registration).

// vi.mock factories are hoisted to module top, so any class they reference
// must be created inside the factory body (vi.hoisted gives a stable handle).
vi.mock("@xterm/xterm", () => {
  class FakeTerminal {
    loadAddon = vi.fn();
    open = vi.fn();
    onData = vi.fn(() => ({ dispose: vi.fn() }));
    onResize = vi.fn(() => ({ dispose: vi.fn() }));
    write = vi.fn();
    resize = vi.fn();
    dispose = vi.fn();
    focus = vi.fn();
    attachCustomKeyEventHandler = vi.fn();
    attachCustomWheelEventHandler = vi.fn();
    getSelection = () => "";
    clearSelection = vi.fn();
    hasSelection = () => false;
    cols = 80;
    rows = 24;
    // ChatPage installs an OSC 52 handler for clipboard pass-through.
    parser = {
      registerOscHandler: vi.fn(() => ({ dispose: vi.fn() })),
    };
    // ChatPage installs a CSI RESIZE escape handler.
    registerCsiHandler = vi.fn();
    // Unicode addon target.
    unicode = { activeVersion: "" };
    // Various accessors xterm exposes that the page touches.
    options = {} as Record<string, unknown>;
    element = document.createElement("div");
    textarea = document.createElement("textarea");
  }
  return { Terminal: FakeTerminal };
});
vi.mock("@xterm/addon-fit", () => ({
  FitAddon: class {
    fit = vi.fn();
    activate = vi.fn();
    dispose = vi.fn();
  },
}));
vi.mock("@xterm/addon-unicode11", () => ({
  Unicode11Addon: class {
    activate = vi.fn();
    dispose = vi.fn();
  },
}));
vi.mock("@xterm/addon-web-links", () => ({
  WebLinksAddon: class {
    activate = vi.fn();
    dispose = vi.fn();
  },
}));
vi.mock("@xterm/addon-webgl", () => ({
  WebglAddon: class {
    activate = vi.fn();
    dispose = vi.fn();
    onContextLoss = vi.fn();
  },
}));
// xterm CSS import — jsdom can't resolve URL imports of CSS via vite.
vi.mock("@xterm/xterm/css/xterm.css", () => ({}));

// Stub WebSocket so the page's connect attempt is inert.
class FakeWebSocket {
  static OPEN = 1;
  static CLOSED = 3;
  readyState = 1;
  onopen: ((e: Event) => void) | null = null;
  onmessage: ((e: MessageEvent) => void) | null = null;
  onclose: ((e: CloseEvent) => void) | null = null;
  onerror: ((e: Event) => void) | null = null;
  binaryType = "arraybuffer";
  constructor(public url: string) {}
  send = vi.fn();
  close = vi.fn();
  addEventListener = vi.fn();
  removeEventListener = vi.fn();
}
// @ts-expect-error — replace the global WebSocket with our inert stub.
globalThis.WebSocket = FakeWebSocket;

const apiMock = vi.hoisted(() => ({
  getSessionLatestDescendant: vi.fn(),
}));
const headerStub = vi.hoisted(() => ({
  setTitle: vi.fn(), setAfterTitle: vi.fn(), setEnd: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  api: apiMock,
  HERMES_BASE_PATH: "",
}));
vi.mock("@/contexts/usePageHeader", () => ({ usePageHeader: () => headerStub }));
vi.mock("@/i18n", () => ({ useI18n: () => ({ t: makeTranslationStub() }) }));
vi.mock("@/plugins", () => ({ PluginSlot: () => null }));
vi.mock("@/components/ChatSidebar", () => ({
  ChatSidebar: () => <aside data-testid="chat-sidebar" />,
}));
vi.mock("@/components/NouiTypography", () => ({
  Typography: ({ children }: any) => <span>{children}</span>,
}));
vi.mock("@nous-research/ui/ui/components/button", () => ({
  Button: ({ children, onClick }: any) => <button onClick={onClick}>{children}</button>,
}));

// jsdom doesn't ship matchMedia / ResizeObserver; xterm + the page poke at
// both during layout setup.  Provide minimal no-op shims so render doesn't
// throw.  Done once globally; safe to leave in place across tests.
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
  // eslint-disable-next-line @typescript-eslint/no-extraneous-class
  class ROStub {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  (window as any).ResizeObserver = ROStub;
}

// Inject a session token before the page reads it on render.
beforeEach(() => {
  (window as any).__HERMES_SESSION_TOKEN__ = "test-session-token";
});

import ChatPage from "./ChatPage";

describe("ChatPage smoke", () => {
  beforeEach(() => {
    apiMock.getSessionLatestDescendant.mockReset();
    headerStub.setEnd.mockClear();
  });
  afterEach(() => cleanup());

  it("renders without crashing in jsdom (xterm + WebSocket fully stubbed)", () => {
    expect(() =>
      render(
        <RouterWrapper>
          <ChatPage />
        </RouterWrapper>,
      ),
    ).not.toThrow();
  });

  it("renders the sidebar component", () => {
    const { getByTestId } = render(
      <RouterWrapper>
        <ChatPage />
      </RouterWrapper>,
    );
    expect(getByTestId("chat-sidebar")).toBeTruthy();
  });

  it("does NOT call getSessionLatestDescendant when no resume param", () => {
    render(
      <RouterWrapper initialEntries={["/chat"]}>
        <ChatPage />
      </RouterWrapper>,
    );
    expect(apiMock.getSessionLatestDescendant).not.toHaveBeenCalled();
  });

  it("calls getSessionLatestDescendant when ?resume=<id> is present", async () => {
    apiMock.getSessionLatestDescendant.mockResolvedValue({
      session_id: "stale-id",
    });
    render(
      <RouterWrapper initialEntries={["/chat?resume=stale-id"]}>
        <ChatPage />
      </RouterWrapper>,
    );
    expect(apiMock.getSessionLatestDescendant).toHaveBeenCalledWith("stale-id");
  });

  it("survives when getSessionLatestDescendant rejects", () => {
    apiMock.getSessionLatestDescendant.mockRejectedValue(new Error("offline"));
    expect(() =>
      render(
        <RouterWrapper initialEntries={["/chat?resume=any"]}>
          <ChatPage />
        </RouterWrapper>,
      ),
    ).not.toThrow();
  });
});
