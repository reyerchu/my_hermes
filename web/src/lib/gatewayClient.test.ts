/**
 * GatewayClient covers the JSON-RPC over WebSocket dialect the dashboard
 * uses to drive the tui_gateway.  We replace global.WebSocket with a
 * controllable stub so connect / request / event dispatch / close are all
 * deterministic.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { GatewayClient } from "./gatewayClient";

interface SentFrame {
  id?: string;
  method: string;
  params?: Record<string, unknown>;
  jsonrpc: string;
}

class FakeWebSocket {
  static OPEN = 1;
  static CLOSED = 3;
  static instances: FakeWebSocket[] = [];

  url: string;
  readyState = 0;
  sent: SentFrame[] = [];
  private listeners: Record<string, ((e: any) => void)[]> = {};

  constructor(url: string) {
    this.url = url;
    FakeWebSocket.instances.push(this);
  }
  addEventListener(name: string, fn: (e: any) => void) {
    (this.listeners[name] ??= []).push(fn);
  }
  removeEventListener(name: string, fn: (e: any) => void) {
    this.listeners[name] = (this.listeners[name] ?? []).filter((l) => l !== fn);
  }
  send(data: string) {
    this.sent.push(JSON.parse(data));
  }
  close() {
    this.readyState = FakeWebSocket.CLOSED;
    this.fire("close", {});
  }
  // Test-only helpers:
  fire(name: string, event: any) {
    for (const fn of this.listeners[name] ?? []) fn(event);
  }
  open() {
    this.readyState = FakeWebSocket.OPEN;
    this.fire("open", {});
  }
  recv(payload: unknown) {
    this.fire("message", { data: JSON.stringify(payload) });
  }
  recvRaw(data: string) {
    this.fire("message", { data });
  }
}

beforeEach(() => {
  FakeWebSocket.instances = [];
  // @ts-expect-error — install stub on the global for the duration of tests.
  globalThis.WebSocket = FakeWebSocket;
  (window as any).__HERMES_SESSION_TOKEN__ = "tok";
  // jsdom uses about:blank, ensure protocol + host are non-empty.
  Object.defineProperty(window, "location", {
    value: { protocol: "http:", host: "127.0.0.1:9119" },
    writable: true,
  });
});

afterEach(() => {
  delete (window as any).__HERMES_SESSION_TOKEN__;
});

async function connectedClient() {
  const gw = new GatewayClient();
  const p = gw.connect();
  FakeWebSocket.instances[0].open();
  await p;
  return { gw, ws: FakeWebSocket.instances[0] };
}

describe("GatewayClient.connect", () => {
  it("starts in idle state", () => {
    const gw = new GatewayClient();
    expect(gw.state).toBe("idle");
  });

  it("transitions idle → connecting → open on successful WebSocket open", async () => {
    const gw = new GatewayClient();
    const seen: string[] = [];
    gw.onState((s) => seen.push(s));
    const p = gw.connect();
    expect(gw.state).toBe("connecting");
    FakeWebSocket.instances[0].open();
    await p;
    expect(gw.state).toBe("open");
    expect(seen).toEqual(["idle", "connecting", "open"]);
  });

  it("uses ws:// for http and wss:// for https", async () => {
    Object.defineProperty(window, "location", {
      value: { protocol: "https:", host: "h.example" },
      writable: true,
    });
    const gw = new GatewayClient();
    const p = gw.connect();
    expect(FakeWebSocket.instances[0].url).toMatch(/^wss:\/\/h\.example/);
    FakeWebSocket.instances[0].open();
    await p;
  });

  it("rejects when no session token is present", async () => {
    delete (window as any).__HERMES_SESSION_TOKEN__;
    const gw = new GatewayClient();
    await expect(gw.connect()).rejects.toThrow(/Session token not available/);
    expect(gw.state).toBe("error");
  });

  it("takes an explicit token argument over the window default", async () => {
    const gw = new GatewayClient();
    const p = gw.connect("override-tok");
    expect(FakeWebSocket.instances[0].url).toContain(
      `token=${encodeURIComponent("override-tok")}`,
    );
    FakeWebSocket.instances[0].open();
    await p;
  });

  it("rejects when WebSocket emits error before open", async () => {
    const gw = new GatewayClient();
    const p = gw.connect();
    FakeWebSocket.instances[0].fire("error", {});
    await expect(p).rejects.toThrow(/WebSocket connection failed/);
    expect(gw.state).toBe("error");
  });

  it("is a no-op when called again while already open", async () => {
    const { gw } = await connectedClient();
    await gw.connect();
    expect(FakeWebSocket.instances.length).toBe(1);
  });
});

describe("GatewayClient.request", () => {
  it("rejects synchronously if not connected", async () => {
    const gw = new GatewayClient();
    await expect(gw.request("anything")).rejects.toThrow(/not connected/);
  });

  it("sends a JSON-RPC 2.0 frame with method, params, and incrementing id", async () => {
    const { gw, ws } = await connectedClient();
    const p1 = gw.request("foo", { x: 1 });
    const p2 = gw.request("bar");
    expect(ws.sent).toHaveLength(2);
    expect(ws.sent[0]).toMatchObject({
      jsonrpc: "2.0",
      method: "foo",
      params: { x: 1 },
    });
    expect(ws.sent[1]).toMatchObject({ method: "bar" });
    // Each id is distinct.
    expect(ws.sent[0].id).not.toEqual(ws.sent[1].id);
    // Resolve them to keep them from hanging the test runner.
    ws.recv({ id: ws.sent[0].id, result: 1 });
    ws.recv({ id: ws.sent[1].id, result: 2 });
    await Promise.all([p1, p2]);
  });

  it("resolves with the result field when the server responds", async () => {
    const { gw, ws } = await connectedClient();
    const p = gw.request<{ session_id: string }>("session.create");
    ws.recv({ id: ws.sent[0].id, result: { session_id: "s-1" } });
    await expect(p).resolves.toEqual({ session_id: "s-1" });
  });

  it("rejects with the server error message", async () => {
    const { gw, ws } = await connectedClient();
    const p = gw.request("nope");
    ws.recv({ id: ws.sent[0].id, error: { message: "method not found" } });
    await expect(p).rejects.toThrow("method not found");
  });

  it("rejects with a synthetic message when error has no .message", async () => {
    const { gw, ws } = await connectedClient();
    const p = gw.request("nope");
    ws.recv({ id: ws.sent[0].id, error: {} });
    await expect(p).rejects.toThrow("request failed");
  });

  it("rejects when the request times out and clears the pending entry", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const { gw } = await connectedClient();
    const p = gw.request("slow", {}, 50);
    vi.advanceTimersByTime(100);
    await expect(p).rejects.toThrow(/timed out: slow/);
    vi.useRealTimers();
  });

  it("rejects in-flight requests when the socket closes", async () => {
    const { gw, ws } = await connectedClient();
    const p = gw.request("any");
    ws.close();
    await expect(p).rejects.toThrow(/closed/);
    expect(gw.state).toBe("closed");
  });
});

describe("GatewayClient event dispatch", () => {
  it("invokes a type-specific listener with the event params", async () => {
    const { ws, gw } = await connectedClient();
    const cb = vi.fn();
    gw.on("message.delta", cb);
    ws.recv({
      method: "event",
      params: { type: "message.delta", session_id: "s", payload: { text: "hi" } },
    });
    expect(cb).toHaveBeenCalledWith({
      type: "message.delta",
      session_id: "s",
      payload: { text: "hi" },
    });
  });

  it("invokes the onAny wildcard listener after the type-specific one", async () => {
    const { ws, gw } = await connectedClient();
    const order: string[] = [];
    gw.on("foo", () => order.push("typed"));
    gw.onAny(() => order.push("any"));
    ws.recv({ method: "event", params: { type: "foo" } });
    expect(order).toEqual(["typed", "any"]);
  });

  it("unsubscribe stops further notifications", async () => {
    const { ws, gw } = await connectedClient();
    const cb = vi.fn();
    const off = gw.on("ev", cb);
    off();
    ws.recv({ method: "event", params: { type: "ev" } });
    expect(cb).not.toHaveBeenCalled();
  });

  it("ignores messages without a method=event (and without a matching id)", async () => {
    const { ws, gw } = await connectedClient();
    const cb = vi.fn();
    gw.onAny(cb);
    ws.recv({ method: "other", params: { type: "ev" } });
    expect(cb).not.toHaveBeenCalled();
  });

  it("ignores events missing a string type field", async () => {
    const { ws, gw } = await connectedClient();
    const cb = vi.fn();
    gw.onAny(cb);
    ws.recv({ method: "event", params: { type: 42 } });
    expect(cb).not.toHaveBeenCalled();
  });

  it("ignores malformed JSON frames silently", async () => {
    const { ws, gw } = await connectedClient();
    const cb = vi.fn();
    gw.onAny(cb);
    expect(() => ws.recvRaw("{not json")).not.toThrow();
    expect(cb).not.toHaveBeenCalled();
  });
});

describe("GatewayClient.close", () => {
  it("clears in-flight pending requests with a rejection", async () => {
    const { gw } = await connectedClient();
    const p = gw.request("any");
    gw.close();
    await expect(p).rejects.toThrow();
  });

  it("multiple close() calls do not throw", async () => {
    const { gw } = await connectedClient();
    expect(() => {
      gw.close();
      gw.close();
    }).not.toThrow();
  });
});
