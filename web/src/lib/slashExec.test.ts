import { describe, it, expect, vi, beforeEach } from "vitest";
import { executeSlash, parseSlash } from "./slashExec";
import type { GatewayClient } from "./gatewayClient";

function makeGw() {
  return {
    request: vi.fn(),
  } as unknown as GatewayClient & { request: ReturnType<typeof vi.fn> };
}

function makeCallbacks() {
  return {
    sys: vi.fn(),
    send: vi.fn(),
  };
}

describe("parseSlash", () => {
  it("parses /name without args", () => {
    expect(parseSlash("/help")).toEqual({ name: "help", arg: "" });
  });

  it("parses /name with args", () => {
    expect(parseSlash("/model opus-4.6")).toEqual({
      name: "model",
      arg: "opus-4.6",
    });
  });

  it("trims trailing whitespace from arg", () => {
    expect(parseSlash("/x   foo   ")).toEqual({ name: "x", arg: "foo" });
  });

  it("accepts multiple leading slashes", () => {
    expect(parseSlash("///compact now")).toEqual({
      name: "compact",
      arg: "now",
    });
  });

  it("returns empty name+arg for blank input", () => {
    expect(parseSlash("/")).toEqual({ name: "", arg: "" });
    expect(parseSlash("")).toEqual({ name: "", arg: "" });
  });
});

describe("executeSlash — slash.exec primary path", () => {
  let gw: ReturnType<typeof makeGw>;
  let cbs: ReturnType<typeof makeCallbacks>;
  beforeEach(() => {
    gw = makeGw();
    cbs = makeCallbacks();
  });

  it("returns 'done' and prints output on slash.exec success", async () => {
    gw.request.mockResolvedValueOnce({ output: "help: ..." });
    const res = await executeSlash({
      command: "/help",
      sessionId: "s1",
      gw,
      callbacks: cbs,
    });
    expect(res).toBe("done");
    expect(cbs.sys).toHaveBeenCalledWith("help: ...");
    expect(gw.request).toHaveBeenCalledWith("slash.exec", {
      command: "help",
      session_id: "s1",
    });
  });

  it("prepends warning text when slash.exec returns warning", async () => {
    gw.request.mockResolvedValueOnce({
      output: "compacted",
      warning: "no recent turns",
    });
    await executeSlash({
      command: "/compact",
      sessionId: "s1",
      gw,
      callbacks: cbs,
    });
    expect(cbs.sys).toHaveBeenCalledWith(
      "warning: no recent turns\ncompacted",
    );
  });

  it("falls back to a synthetic message if output is empty", async () => {
    gw.request.mockResolvedValueOnce({ output: "" });
    await executeSlash({
      command: "/help",
      sessionId: "s1",
      gw,
      callbacks: cbs,
    });
    expect(cbs.sys).toHaveBeenCalledWith("/help: no output");
  });

  it("returns 'error' for an empty command", async () => {
    const res = await executeSlash({
      command: "/",
      sessionId: "s1",
      gw,
      callbacks: cbs,
    });
    expect(res).toBe("error");
    expect(cbs.sys).toHaveBeenCalledWith("empty slash command");
    expect(gw.request).not.toHaveBeenCalled();
  });
});

describe("executeSlash — command.dispatch fallback", () => {
  let gw: ReturnType<typeof makeGw>;
  let cbs: ReturnType<typeof makeCallbacks>;
  beforeEach(() => {
    gw = makeGw();
    cbs = makeCallbacks();
  });

  it("dispatches 'exec' directive output", async () => {
    gw.request
      .mockRejectedValueOnce(new Error("not handled"))
      .mockResolvedValueOnce({ type: "exec", output: "ran" });
    const res = await executeSlash({
      command: "/foo",
      sessionId: "s1",
      gw,
      callbacks: cbs,
    });
    expect(res).toBe("done");
    expect(cbs.sys).toHaveBeenCalledWith("ran");
  });

  it("dispatches 'plugin' directive with no output → '(no output)'", async () => {
    gw.request
      .mockRejectedValueOnce(new Error("primary failed"))
      .mockResolvedValueOnce({ type: "plugin" });
    await executeSlash({
      command: "/cron list",
      sessionId: "s1",
      gw,
      callbacks: cbs,
    });
    expect(cbs.sys).toHaveBeenCalledWith("(no output)");
  });

  it("'send' directive submits the message and returns 'sent'", async () => {
    gw.request
      .mockRejectedValueOnce(new Error("primary"))
      .mockResolvedValueOnce({ type: "send", message: "hello" });
    const res = await executeSlash({
      command: "/say hi",
      sessionId: "s1",
      gw,
      callbacks: cbs,
    });
    expect(res).toBe("sent");
    expect(cbs.send).toHaveBeenCalledWith("hello");
  });

  it("'send' with empty message returns 'error'", async () => {
    gw.request
      .mockRejectedValueOnce(new Error("primary"))
      .mockResolvedValueOnce({ type: "send", message: "" });
    const res = await executeSlash({
      command: "/say",
      sessionId: "s1",
      gw,
      callbacks: cbs,
    });
    expect(res).toBe("error");
    expect(cbs.send).not.toHaveBeenCalled();
  });

  it("'skill' directive logs marker and sends the message", async () => {
    gw.request
      .mockRejectedValueOnce(new Error("primary"))
      .mockResolvedValueOnce({
        type: "skill",
        name: "review",
        message: "do review",
      });
    const res = await executeSlash({
      command: "/review",
      sessionId: "s1",
      gw,
      callbacks: cbs,
    });
    expect(res).toBe("sent");
    expect(cbs.sys).toHaveBeenCalledWith("⚡ loading skill: review");
    expect(cbs.send).toHaveBeenCalledWith("do review");
  });

  it("'alias' directive recursively runs the target command", async () => {
    gw.request
      .mockRejectedValueOnce(new Error("primary"))
      .mockResolvedValueOnce({ type: "alias", target: "help" })
      .mockResolvedValueOnce({ output: "help text" });
    const res = await executeSlash({
      command: "/h",
      sessionId: "s1",
      gw,
      callbacks: cbs,
    });
    expect(res).toBe("done");
    expect(gw.request).toHaveBeenLastCalledWith("slash.exec", {
      command: "help",
      session_id: "s1",
    });
  });

  it("returns 'error' on unrecognised dispatch type", async () => {
    gw.request
      .mockRejectedValueOnce(new Error("primary"))
      .mockResolvedValueOnce({ type: "unknown" });
    const res = await executeSlash({
      command: "/x",
      sessionId: "s1",
      gw,
      callbacks: cbs,
    });
    expect(res).toBe("error");
    expect(cbs.sys).toHaveBeenCalledWith("error: invalid response: command.dispatch");
  });

  it("returns 'error' when command.dispatch itself throws", async () => {
    gw.request
      .mockRejectedValueOnce(new Error("primary"))
      .mockRejectedValueOnce(new Error("boom"));
    const res = await executeSlash({
      command: "/x",
      sessionId: "s1",
      gw,
      callbacks: cbs,
    });
    expect(res).toBe("error");
    expect(cbs.sys).toHaveBeenCalledWith("error: boom");
  });
});
