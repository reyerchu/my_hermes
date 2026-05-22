import { describe, it, expect, afterEach } from "vitest";
import { isDashboardEmbeddedChatEnabled } from "./dashboard-flags";

declare global {
  interface Window {
    __HERMES_DASHBOARD_EMBEDDED_CHAT__?: boolean;
    __HERMES_DASHBOARD_TUI__?: boolean;
  }
}

describe("isDashboardEmbeddedChatEnabled", () => {
  afterEach(() => {
    delete window.__HERMES_DASHBOARD_EMBEDDED_CHAT__;
    delete window.__HERMES_DASHBOARD_TUI__;
  });

  it("returns false when no window flags are set", () => {
    expect(isDashboardEmbeddedChatEnabled()).toBe(false);
  });

  it("returns true when the new flag is true", () => {
    window.__HERMES_DASHBOARD_EMBEDDED_CHAT__ = true;
    expect(isDashboardEmbeddedChatEnabled()).toBe(true);
  });

  it("returns true when only the legacy TUI flag is true", () => {
    window.__HERMES_DASHBOARD_TUI__ = true;
    expect(isDashboardEmbeddedChatEnabled()).toBe(true);
  });

  it("treats falsy new flag as off even with legacy true (legacy still wins)", () => {
    window.__HERMES_DASHBOARD_EMBEDDED_CHAT__ = false;
    window.__HERMES_DASHBOARD_TUI__ = true;
    expect(isDashboardEmbeddedChatEnabled()).toBe(true);
  });

  it("returns false when both flags are explicitly false", () => {
    window.__HERMES_DASHBOARD_EMBEDDED_CHAT__ = false;
    window.__HERMES_DASHBOARD_TUI__ = false;
    expect(isDashboardEmbeddedChatEnabled()).toBe(false);
  });
});
