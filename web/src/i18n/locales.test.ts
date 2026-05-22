/**
 * Locale-data consistency checks.  Each locale bundle ships as a separate
 * TS module so a single missed translation would silently degrade only
 * that one language.  These tests catch the entire class:
 *
 *   * every bundle exists and is importable
 *   * every bundle has the same nested key structure as the canonical
 *     English bundle
 *   * every leaf is a non-empty string (no accidental empty stubs)
 */
import { describe, it, expect } from "vitest";
import { en } from "./en";
import { zh } from "./zh";
import { zhHant } from "./zh-hant";
import { ja } from "./ja";
import { de } from "./de";
import { es } from "./es";
import { fr } from "./fr";
import { tr } from "./tr";
import { uk } from "./uk";
import { af } from "./af";
import { ko } from "./ko";
import { it as it_ } from "./it";
import { ga } from "./ga";
import { pt } from "./pt";
import { ru } from "./ru";
import { hu } from "./hu";
import type { Translations } from "./types";

const ALL_LOCALES: Array<{ code: string; bundle: Translations }> = [
  { code: "en", bundle: en },
  { code: "zh", bundle: zh },
  { code: "zh-hant", bundle: zhHant },
  { code: "ja", bundle: ja },
  { code: "de", bundle: de },
  { code: "es", bundle: es },
  { code: "fr", bundle: fr },
  { code: "tr", bundle: tr },
  { code: "uk", bundle: uk },
  { code: "af", bundle: af },
  { code: "ko", bundle: ko },
  { code: "it", bundle: it_ },
  { code: "ga", bundle: ga },
  { code: "pt", bundle: pt },
  { code: "ru", bundle: ru },
  { code: "hu", bundle: hu },
];

/** Flatten a translations object to a sorted list of dotted key paths. */
function flattenKeys(obj: unknown, prefix = ""): string[] {
  if (typeof obj !== "object" || obj === null) return [prefix];
  const keys: string[] = [];
  for (const [k, v] of Object.entries(obj)) {
    keys.push(...flattenKeys(v, prefix ? `${prefix}.${k}` : k));
  }
  return keys.sort();
}

describe("locale bundle existence", () => {
  it("every supported locale ships a bundle", () => {
    expect(ALL_LOCALES).toHaveLength(16);
    for (const { code, bundle } of ALL_LOCALES) {
      expect(bundle).toBeDefined();
      expect(bundle).not.toBeNull();
      // app.nav is on every page → cheapest "real bundle" signal.
      expect((bundle as any).app?.nav).toBeDefined();
      void code;
    }
  });
});

describe("locale bundle shape parity", () => {
  const canonical = flattenKeys(en);

  for (const { code, bundle } of ALL_LOCALES) {
    if (code === "en") continue;
    it(`'${code}' has the same key structure as 'en'`, () => {
      const here = flattenKeys(bundle);
      // Use array intersections to give a useful diff when something
      // drifts — instead of failing on "lengths differ".
      const missing = canonical.filter((k) => !here.includes(k));
      const extra = here.filter((k) => !canonical.includes(k));
      expect({ missing, extra }).toEqual({ missing: [], extra: [] });
    });
  }
});

describe("no empty translation leaves", () => {
  function collectLeaves(obj: unknown, prefix = ""): Array<[string, unknown]> {
    if (typeof obj !== "object" || obj === null) return [[prefix, obj]];
    const out: Array<[string, unknown]> = [];
    for (const [k, v] of Object.entries(obj)) {
      out.push(
        ...collectLeaves(v, prefix ? `${prefix}.${k}` : k),
      );
    }
    return out;
  }

  for (const { code, bundle } of ALL_LOCALES) {
    it(`'${code}' has no empty-string leaves`, () => {
      const empties = collectLeaves(bundle)
        .filter(([, v]) => typeof v === "string" && v.trim() === "")
        .map(([k]) => k);
      expect(empties).toEqual([]);
    });
  }
});
