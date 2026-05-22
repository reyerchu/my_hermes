/**
 * api.ts coverage — the dashboard's fetch wrapper.  Mock global.fetch so
 * we can assert URL composition, header injection, body serialisation,
 * error path, and base-path handling without a running server.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// HERMES_BASE_PATH is captured at module-import time from window.__HERMES_BASE_PATH__.
// Set that BEFORE importing so the prefixing test can verify it works.

beforeEach(() => {
  // Default: served at root, valid session token.
  (window as any).__HERMES_SESSION_TOKEN__ = "test-tok";
  delete (window as any).__HERMES_BASE_PATH__;
  vi.resetModules();
});

afterEach(() => {
  delete (window as any).__HERMES_SESSION_TOKEN__;
  delete (window as any).__HERMES_BASE_PATH__;
});

async function makeFetch(response: {
  ok: boolean;
  status?: number;
  body?: unknown;
  statusText?: string;
}) {
  const mock = vi.fn().mockResolvedValue({
    ok: response.ok,
    status: response.status ?? (response.ok ? 200 : 500),
    statusText: response.statusText ?? (response.ok ? "OK" : "Server Error"),
    json: async () => response.body,
    text: async () =>
      typeof response.body === "string"
        ? response.body
        : JSON.stringify(response.body ?? ""),
  });
  globalThis.fetch = mock as unknown as typeof fetch;
  return mock;
}

describe("fetchJSON", () => {
  it("injects the session token header on every call", async () => {
    const fetchMock = await makeFetch({ ok: true, body: { ok: true } });
    const { fetchJSON } = await import("./api");
    await fetchJSON("/api/status");
    const init = fetchMock.mock.calls[0][1];
    const headers = init.headers as Headers;
    expect(headers.get("X-Hermes-Session-Token")).toBe("test-tok");
  });

  it("returns the parsed JSON body on success", async () => {
    await makeFetch({ ok: true, body: { hello: "world" } });
    const { fetchJSON } = await import("./api");
    await expect(fetchJSON("/api/anything")).resolves.toEqual({ hello: "world" });
  });

  it("throws an Error containing status + text on a non-OK response", async () => {
    await makeFetch({
      ok: false,
      status: 404,
      body: "not found",
    });
    const { fetchJSON } = await import("./api");
    await expect(fetchJSON("/api/missing")).rejects.toThrow(/404.*not found/);
  });

  it("does not override a caller-supplied X-Hermes-Session-Token", async () => {
    const fetchMock = await makeFetch({ ok: true, body: {} });
    const { fetchJSON } = await import("./api");
    await fetchJSON("/api/x", {
      headers: { "X-Hermes-Session-Token": "explicit" },
    });
    const init = fetchMock.mock.calls[0][1];
    const headers = init.headers as Headers;
    expect(headers.get("X-Hermes-Session-Token")).toBe("explicit");
  });

  it("preserves caller-supplied method, body, and Content-Type", async () => {
    const fetchMock = await makeFetch({ ok: true, body: {} });
    const { fetchJSON } = await import("./api");
    await fetchJSON("/api/x", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ a: 1 }),
    });
    const init = fetchMock.mock.calls[0][1];
    expect(init.method).toBe("POST");
    expect(init.body).toBe('{"a":1}');
    expect((init.headers as Headers).get("Content-Type")).toBe(
      "application/json",
    );
  });
});

describe("HERMES_BASE_PATH prefixing", () => {
  it("prefixes API URLs when the server injected a base path", async () => {
    (window as any).__HERMES_BASE_PATH__ = "/hermes";
    const fetchMock = await makeFetch({ ok: true, body: {} });
    const { fetchJSON, HERMES_BASE_PATH } = await import("./api");
    expect(HERMES_BASE_PATH).toBe("/hermes");
    await fetchJSON("/api/status");
    expect(fetchMock.mock.calls[0][0]).toBe("/hermes/api/status");
  });

  it("normalises a base path without a leading slash", async () => {
    (window as any).__HERMES_BASE_PATH__ = "tilos/hermes";
    const fetchMock = await makeFetch({ ok: true, body: {} });
    const { fetchJSON } = await import("./api");
    await fetchJSON("/api/x");
    expect(fetchMock.mock.calls[0][0]).toBe("/tilos/hermes/api/x");
  });

  it("strips a trailing slash from the base path", async () => {
    (window as any).__HERMES_BASE_PATH__ = "/proxy/";
    const fetchMock = await makeFetch({ ok: true, body: {} });
    const { fetchJSON } = await import("./api");
    await fetchJSON("/api/x");
    expect(fetchMock.mock.calls[0][0]).toBe("/proxy/api/x");
  });

  it("defaults to no prefix (served at root)", async () => {
    const fetchMock = await makeFetch({ ok: true, body: {} });
    const { fetchJSON, HERMES_BASE_PATH } = await import("./api");
    expect(HERMES_BASE_PATH).toBe("");
    await fetchJSON("/api/x");
    expect(fetchMock.mock.calls[0][0]).toBe("/api/x");
  });
});

describe("api endpoint wrappers", () => {
  it("api.getStatus hits /api/status", async () => {
    const fetchMock = await makeFetch({ ok: true, body: { ok: true } });
    const { api } = await import("./api");
    await api.getStatus();
    expect(fetchMock.mock.calls[0][0]).toBe("/api/status");
  });

  it("api.getSessions(limit, offset) puts both in the query string", async () => {
    const fetchMock = await makeFetch({
      ok: true,
      body: { sessions: [], total: 0 },
    });
    const { api } = await import("./api");
    await api.getSessions(25, 50);
    expect(fetchMock.mock.calls[0][0]).toBe("/api/sessions?limit=25&offset=50");
  });

  it("api.deleteSession sends DELETE on the URL-encoded id", async () => {
    const fetchMock = await makeFetch({ ok: true, body: { ok: true } });
    const { api } = await import("./api");
    await api.deleteSession("session/with slashes");
    expect(fetchMock.mock.calls[0][0]).toBe(
      "/api/sessions/session%2Fwith%20slashes",
    );
    expect(fetchMock.mock.calls[0][1].method).toBe("DELETE");
  });

  it("api.getLogs only includes set params and skips ALL/all", async () => {
    const fetchMock = await makeFetch({ ok: true, body: { lines: [] } });
    const { api } = await import("./api");
    await api.getLogs({
      file: "agent",
      lines: 100,
      level: "ALL",
      component: "all",
    });
    const url = fetchMock.mock.calls[0][0] as string;
    expect(url).toContain("file=agent");
    expect(url).toContain("lines=100");
    expect(url).not.toContain("level=");
    expect(url).not.toContain("component=");
  });

  it("api.saveConfig sends PUT with JSON body wrapped in {config: …}", async () => {
    const fetchMock = await makeFetch({ ok: true, body: { ok: true } });
    const { api } = await import("./api");
    await api.saveConfig({ a: 1 });
    const init = fetchMock.mock.calls[0][1];
    expect(init.method).toBe("PUT");
    expect(init.body).toBe(JSON.stringify({ config: { a: 1 } }));
  });

  it("api.setEnvVar sends PUT with {key, value} body", async () => {
    const fetchMock = await makeFetch({ ok: true, body: { ok: true } });
    const { api } = await import("./api");
    await api.setEnvVar("MY_KEY", "secret");
    expect(fetchMock.mock.calls[0][1].body).toBe(
      JSON.stringify({ key: "MY_KEY", value: "secret" }),
    );
  });
});
