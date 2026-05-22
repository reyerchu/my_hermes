import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { cn, timeAgo, isoTimeAgo } from "./utils";

describe("cn", () => {
  it("merges plain strings", () => {
    expect(cn("a", "b")).toBe("a b");
  });

  it("filters falsy values", () => {
    expect(cn("a", false, null, undefined, "", "b")).toBe("a b");
  });

  it("accepts conditional objects", () => {
    expect(cn("base", { active: true, hidden: false })).toBe("base active");
  });

  it("dedupes conflicting tailwind classes (last wins)", () => {
    // tailwind-merge keeps the rightmost padding-x class.
    expect(cn("px-2", "px-4")).toBe("px-4");
  });

  it("accepts nested arrays", () => {
    expect(cn(["a", ["b", "c"]])).toBe("a b c");
  });
});

describe("timeAgo", () => {
  // Pin "now" to 2026-01-01T00:00:00Z so deltas are deterministic.
  const NOW_MS = 1_767_225_600_000;
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(NOW_MS));
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  const nowSec = NOW_MS / 1000;

  it("returns 'just now' for sub-minute deltas", () => {
    expect(timeAgo(nowSec)).toBe("just now");
    expect(timeAgo(nowSec - 30)).toBe("just now");
    expect(timeAgo(nowSec - 59)).toBe("just now");
  });

  it("returns minutes for sub-hour deltas", () => {
    expect(timeAgo(nowSec - 60)).toBe("1m ago");
    expect(timeAgo(nowSec - 600)).toBe("10m ago");
    expect(timeAgo(nowSec - 3599)).toBe("59m ago");
  });

  it("returns hours for sub-day deltas", () => {
    expect(timeAgo(nowSec - 3600)).toBe("1h ago");
    expect(timeAgo(nowSec - 86_399)).toBe("23h ago");
  });

  it("returns 'yesterday' for 24–48h deltas", () => {
    expect(timeAgo(nowSec - 86_400)).toBe("yesterday");
    expect(timeAgo(nowSec - 172_799)).toBe("yesterday");
  });

  it("returns days for older deltas", () => {
    expect(timeAgo(nowSec - 172_800)).toBe("2d ago");
    expect(timeAgo(nowSec - 7 * 86_400)).toBe("7d ago");
  });
});

describe("isoTimeAgo", () => {
  const NOW_MS = 1_767_225_600_000;
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(NOW_MS));
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("returns 'just now' for a recent ISO timestamp", () => {
    const iso = new Date(NOW_MS - 5_000).toISOString();
    expect(isoTimeAgo(iso)).toBe("just now");
  });

  it("returns minutes / hours / days like timeAgo", () => {
    expect(isoTimeAgo(new Date(NOW_MS - 120_000).toISOString())).toBe("2m ago");
    expect(isoTimeAgo(new Date(NOW_MS - 7_200_000).toISOString())).toBe("2h ago");
    expect(isoTimeAgo(new Date(NOW_MS - 2 * 86_400_000).toISOString())).toBe("2d ago");
  });

  it("returns 'unknown' for invalid ISO input", () => {
    expect(isoTimeAgo("not-a-date")).toBe("unknown");
  });

  it("returns 'unknown' for a future timestamp", () => {
    expect(isoTimeAgo(new Date(NOW_MS + 60_000).toISOString())).toBe("unknown");
  });
});
