import { describe, it, expect, vi, afterEach } from "vitest";
import { render, cleanup } from "@testing-library/react";

// ChatSidebar instantiates GatewayClient + opens an /api/events SSE-style
// stream.  Stub both so the test doesn't try to open real WebSockets.

const gwInstances = vi.hoisted(() => ({ list: [] as any[] }));

vi.mock("@/lib/gatewayClient", () => {
  class FakeGatewayClient {
    state = "idle";
    on = vi.fn(() => () => {});
    onAny = vi.fn(() => () => {});
    onState = vi.fn((cb: any) => {
      cb("idle");
      return () => {};
    });
    connect = vi.fn().mockResolvedValue(undefined);
    close = vi.fn();
    request = vi.fn().mockResolvedValue({ session_id: "s-1" });
    constructor() {
      gwInstances.list.push(this);
    }
  }
  return { GatewayClient: FakeGatewayClient };
});

vi.mock("@/components/ModelPickerDialog", () => ({
  ModelPickerDialog: () => null,
}));
vi.mock("@/components/ToolCall", () => ({
  ToolCall: ({ tool }: any) => <div data-tool>{tool.name}</div>,
}));
vi.mock("@nous-research/ui/ui/components/badge", () => ({
  Badge: ({ children }: any) => <span>{children}</span>,
}));
vi.mock("@nous-research/ui/ui/components/button", () => ({
  Button: ({ children, onClick, disabled }: any) => (
    <button onClick={onClick} disabled={disabled}>{children}</button>
  ),
}));

// EventSource doesn't exist in jsdom; stub it so subscribing to the events
// stream is inert.
(globalThis as any).EventSource = class {
  url: string;
  onmessage: ((e: MessageEvent) => void) | null = null;
  onerror: ((e: Event) => void) | null = null;
  constructor(url: string) {
    this.url = url;
  }
  close() {}
  addEventListener() {}
};

import { ChatSidebar } from "./ChatSidebar";

afterEach(() => {
  cleanup();
  gwInstances.list = [];
});

describe("ChatSidebar smoke", () => {
  it("renders without crashing", () => {
    expect(() => render(<ChatSidebar channel="ch-1" />)).not.toThrow();
  });

  it("instantiates a GatewayClient on mount", () => {
    render(<ChatSidebar channel="ch-1" />);
    expect(gwInstances.list.length).toBeGreaterThan(0);
  });

  it("calls gw.connect() on mount", () => {
    render(<ChatSidebar channel="ch-1" />);
    expect(gwInstances.list[0].connect).toHaveBeenCalled();
  });

  it("subscribes to onState for connection-state changes", () => {
    render(<ChatSidebar channel="ch-1" />);
    expect(gwInstances.list[0].onState).toHaveBeenCalled();
  });

  it("subscribes to session.info and error events", () => {
    render(<ChatSidebar channel="ch-1" />);
    const on = gwInstances.list[0].on;
    const types = on.mock.calls.map((c: any[]) => c[0]);
    expect(types).toContain("session.info");
    expect(types).toContain("error");
  });
});
