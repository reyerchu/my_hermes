import { describe, it, expect } from "vitest";
import { getNestedValue, setNestedValue } from "./nested";

describe("getNestedValue", () => {
  it("returns the top-level value for a single key", () => {
    expect(getNestedValue({ a: 1 }, "a")).toBe(1);
  });

  it("traverses nested object paths", () => {
    expect(getNestedValue({ a: { b: { c: 42 } } }, "a.b.c")).toBe(42);
  });

  it("returns undefined when a segment is missing", () => {
    expect(getNestedValue({ a: { b: 1 } }, "a.c")).toBeUndefined();
  });

  it("returns undefined when descending through a non-object", () => {
    expect(getNestedValue({ a: 5 }, "a.b")).toBeUndefined();
  });

  it("returns undefined for an empty object regardless of path", () => {
    expect(getNestedValue({}, "anything")).toBeUndefined();
  });

  it("handles null intermediate values without throwing", () => {
    expect(getNestedValue({ a: null } as Record<string, unknown>, "a.b")).toBeUndefined();
  });
});

describe("setNestedValue", () => {
  it("does not mutate the input object", () => {
    const input = { a: 1 };
    const output = setNestedValue(input, "b", 2);
    expect(input).toEqual({ a: 1 });
    expect(output).toEqual({ a: 1, b: 2 });
  });

  it("sets a top-level value", () => {
    expect(setNestedValue({}, "x", 10)).toEqual({ x: 10 });
  });

  it("creates intermediate objects when missing", () => {
    expect(setNestedValue({}, "a.b.c", 7)).toEqual({ a: { b: { c: 7 } } });
  });

  it("overwrites a non-object intermediate without crashing", () => {
    // Existing leaf string is replaced by an object so the path can land.
    expect(setNestedValue({ a: "scalar" }, "a.b", 9)).toEqual({ a: { b: 9 } });
  });

  it("preserves siblings on the same level", () => {
    expect(setNestedValue({ a: { b: 1, c: 2 } }, "a.b", 9)).toEqual({
      a: { b: 9, c: 2 },
    });
  });

  it("can write null and undefined values", () => {
    expect(setNestedValue({ a: 1 }, "a", null)).toEqual({ a: null });
    expect(setNestedValue({ a: 1 }, "a", undefined)).toEqual({ a: undefined });
  });

  it("deep-clones nested input so mutations to result don't bleed back", () => {
    const input = { a: { b: { c: 1 } } };
    const output = setNestedValue(input, "a.b.c", 2) as { a: { b: { c: number } } };
    output.a.b.c = 999;
    expect(input.a.b.c).toBe(1);
  });
});
