/**
 * Coverage for the plugin slot registry — the public contract between
 * the dashboard shell and bundled plugins.
 *
 * The registry is module-scoped state, so each test starts by clearing
 * any leftover entries via unregisterPluginSlots to avoid cross-test
 * contamination.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render } from "@testing-library/react";
import {
  KNOWN_SLOT_NAMES,
  PluginSlot,
  getSlotEntries,
  onSlotRegistered,
  registerSlot,
  unregisterPluginSlots,
} from "./slots";

function PluginA() {
  return <div data-testid="plugin-a">A</div>;
}
function PluginB() {
  return <div data-testid="plugin-b">B</div>;
}

function reset() {
  unregisterPluginSlots("plugin-a");
  unregisterPluginSlots("plugin-b");
  unregisterPluginSlots("plugin-c");
}

beforeEach(reset);

describe("KNOWN_SLOT_NAMES", () => {
  it("contains the shell-wide slots", () => {
    expect(KNOWN_SLOT_NAMES).toContain("header-left");
    expect(KNOWN_SLOT_NAMES).toContain("header-right");
    expect(KNOWN_SLOT_NAMES).toContain("backdrop");
    expect(KNOWN_SLOT_NAMES).toContain("sidebar");
  });

  it("contains the per-page top/bottom slots for every built-in route", () => {
    for (const page of [
      "sessions", "analytics", "logs", "cron", "skills",
      "plugins", "config", "env", "docs", "chat",
    ]) {
      expect(KNOWN_SLOT_NAMES).toContain(`${page}:top`);
      expect(KNOWN_SLOT_NAMES).toContain(`${page}:bottom`);
    }
  });
});

describe("registerSlot + getSlotEntries", () => {
  it("starts empty for any slot", () => {
    expect(getSlotEntries("test-slot")).toEqual([]);
  });

  it("registers a component and exposes it via getSlotEntries", () => {
    registerSlot("plugin-a", "test-slot", PluginA);
    const entries = getSlotEntries("test-slot");
    expect(entries).toHaveLength(1);
    expect(entries[0].plugin).toBe("plugin-a");
    expect(entries[0].component).toBe(PluginA);
  });

  it("appends entries from multiple plugins in registration order", () => {
    registerSlot("plugin-a", "test-slot", PluginA);
    registerSlot("plugin-b", "test-slot", PluginB);
    const entries = getSlotEntries("test-slot");
    expect(entries.map((e) => e.plugin)).toEqual(["plugin-a", "plugin-b"]);
  });

  it("replaces a re-registered (plugin, slot) entry without duplicating", () => {
    registerSlot("plugin-a", "test-slot", PluginA);
    registerSlot("plugin-a", "test-slot", PluginB);
    const entries = getSlotEntries("test-slot");
    expect(entries).toHaveLength(1);
    expect(entries[0].component).toBe(PluginB);
  });

  it("returns a copy from getSlotEntries — mutations don't leak", () => {
    registerSlot("plugin-a", "test-slot", PluginA);
    const entries = getSlotEntries("test-slot");
    entries.length = 0;
    expect(getSlotEntries("test-slot")).toHaveLength(1);
  });
});

describe("unregisterPluginSlots", () => {
  it("removes that plugin's entries across all slots", () => {
    registerSlot("plugin-a", "slot-1", PluginA);
    registerSlot("plugin-a", "slot-2", PluginA);
    registerSlot("plugin-b", "slot-1", PluginB);
    unregisterPluginSlots("plugin-a");
    expect(getSlotEntries("slot-1").map((e) => e.plugin)).toEqual(["plugin-b"]);
    expect(getSlotEntries("slot-2")).toEqual([]);
  });

  it("is a safe no-op when the plugin had no entries", () => {
    expect(() => unregisterPluginSlots("plugin-c")).not.toThrow();
  });
});

describe("onSlotRegistered", () => {
  it("fires on register and unregister", () => {
    const listener = vi.fn();
    const unsub = onSlotRegistered(listener);
    registerSlot("plugin-a", "slot-1", PluginA);
    expect(listener).toHaveBeenCalled();
    listener.mockClear();
    unregisterPluginSlots("plugin-a");
    expect(listener).toHaveBeenCalled();
    unsub();
  });

  it("stops firing after unsubscribe", () => {
    const listener = vi.fn();
    const unsub = onSlotRegistered(listener);
    unsub();
    registerSlot("plugin-a", "slot-1", PluginA);
    expect(listener).not.toHaveBeenCalled();
  });

  it("a throwing listener does not break notify for other listeners", () => {
    const ok = vi.fn();
    const bad = () => {
      throw new Error("listener blew up");
    };
    onSlotRegistered(bad);
    onSlotRegistered(ok);
    registerSlot("plugin-a", "slot-1", PluginA);
    expect(ok).toHaveBeenCalled();
  });
});

describe("PluginSlot component", () => {
  it("renders fallback when no plugin has registered for the slot", () => {
    const { container } = render(
      <PluginSlot name="empty-slot" fallback={<span data-testid="fb">fb</span>} />,
    );
    expect(container.querySelector("[data-testid='fb']")).not.toBeNull();
  });

  it("renders null when no plugins and no fallback", () => {
    const { container } = render(<PluginSlot name="empty-slot" />);
    expect(container.firstChild).toBeNull();
  });

  it("renders every registered component", () => {
    registerSlot("plugin-a", "render-slot", PluginA);
    registerSlot("plugin-b", "render-slot", PluginB);
    const { getByTestId } = render(<PluginSlot name="render-slot" />);
    expect(getByTestId("plugin-a")).toBeTruthy();
    expect(getByTestId("plugin-b")).toBeTruthy();
  });

  it("picks up a plugin registered after mount via the subscription", async () => {
    const { findByTestId, container } = render(
      <PluginSlot name="late-slot" />,
    );
    // No fallback, no registrations yet → empty.
    expect(container.firstChild).toBeNull();
    registerSlot("plugin-a", "late-slot", PluginA);
    expect(await findByTestId("plugin-a")).toBeTruthy();
  });
});
