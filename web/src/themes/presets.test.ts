import { describe, it, expect } from "vitest";
import {
  BUILTIN_THEMES,
  defaultTheme,
  defaultLargeTheme,
} from "./presets";

describe("BUILTIN_THEMES", () => {
  it("contains the named built-in palettes", () => {
    for (const expected of [
      "default", "midnight", "ember", "mono", "cyberpunk", "rose",
    ]) {
      expect(BUILTIN_THEMES[expected]).toBeDefined();
    }
  });

  it("every theme has the required shape", () => {
    for (const theme of Object.values(BUILTIN_THEMES)) {
      expect(typeof theme.name).toBe("string");
      expect(theme.name.length).toBeGreaterThan(0);
      expect(typeof theme.label).toBe("string");
      expect(theme.palette).toBeDefined();
      expect(theme.palette.background).toBeDefined();
      expect(theme.palette.midground).toBeDefined();
      expect(theme.palette.foreground).toBeDefined();
    }
  });

  it("every palette layer carries a hex colour and an alpha", () => {
    for (const theme of Object.values(BUILTIN_THEMES)) {
      for (const layerName of [
        "background", "midground", "foreground",
      ] as const) {
        const layer = theme.palette[layerName];
        expect(typeof layer.hex).toBe("string");
        expect(layer.hex).toMatch(/^#?[0-9A-Fa-f]+/);
        expect(typeof layer.alpha).toBe("number");
        expect(layer.alpha).toBeGreaterThanOrEqual(0);
        expect(layer.alpha).toBeLessThanOrEqual(1);
      }
    }
  });

  it("defaultTheme is named 'default'", () => {
    expect(defaultTheme.name).toBe("default");
  });

  it("defaultLargeTheme shares the palette of defaultTheme", () => {
    expect(defaultLargeTheme.palette).toBe(defaultTheme.palette);
  });

  it("defaultLargeTheme is a distinct entry from defaultTheme", () => {
    expect(defaultLargeTheme.name).not.toBe(defaultTheme.name);
  });

  it("theme names are unique", () => {
    const names = Object.values(BUILTIN_THEMES).map((t) => t.name);
    expect(new Set(names).size).toBe(names.length);
  });
});
