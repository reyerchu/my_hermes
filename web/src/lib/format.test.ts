import { describe, it, expect } from "vitest";
import { formatTokenCount } from "./format";

describe("formatTokenCount", () => {
  it("returns raw integer string for values under 1k", () => {
    expect(formatTokenCount(0)).toBe("0");
    expect(formatTokenCount(1)).toBe("1");
    expect(formatTokenCount(42)).toBe("42");
    expect(formatTokenCount(999)).toBe("999");
  });

  it("formats thousands with K suffix and drops trailing .0", () => {
    expect(formatTokenCount(1_000)).toBe("1K");
    expect(formatTokenCount(4_000)).toBe("4K");
    expect(formatTokenCount(128_000)).toBe("128K");
  });

  it("keeps a single decimal when not a round thousand", () => {
    expect(formatTokenCount(1_500)).toBe("1.5K");
    expect(formatTokenCount(4_096)).toBe("4.1K");
  });

  it("formats millions with M suffix and drops trailing .0", () => {
    expect(formatTokenCount(1_000_000)).toBe("1M");
    expect(formatTokenCount(2_000_000)).toBe("2M");
  });

  it("keeps a single decimal for non-round millions", () => {
    expect(formatTokenCount(1_500_000)).toBe("1.5M");
    expect(formatTokenCount(2_750_000)).toBe("2.8M");
  });

  it("breakpoint exactly at 1k uses K, not bare integer", () => {
    expect(formatTokenCount(999)).toBe("999");
    expect(formatTokenCount(1_000)).toBe("1K");
  });

  it("breakpoint exactly at 1M uses M, not K", () => {
    expect(formatTokenCount(999_999)).toBe("1000.0K");
    expect(formatTokenCount(1_000_000)).toBe("1M");
  });
});
