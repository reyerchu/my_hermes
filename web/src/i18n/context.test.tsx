import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { act, render, renderHook } from "@testing-library/react";
import { I18nProvider, useI18n, LOCALE_META } from "./context";

function wrapper({ children }: { children: React.ReactNode }) {
  return <I18nProvider>{children}</I18nProvider>;
}

beforeEach(() => {
  localStorage.clear();
});

afterEach(() => {
  localStorage.clear();
});

describe("I18nProvider initial locale", () => {
  it("defaults to 'en' when localStorage is empty", () => {
    const { result } = renderHook(() => useI18n(), { wrapper });
    expect(result.current.locale).toBe("en");
  });

  it("loads a persisted locale from localStorage", () => {
    localStorage.setItem("hermes-locale", "ja");
    const { result } = renderHook(() => useI18n(), { wrapper });
    expect(result.current.locale).toBe("ja");
  });

  it("ignores an unsupported persisted locale", () => {
    localStorage.setItem("hermes-locale", "klingon");
    const { result } = renderHook(() => useI18n(), { wrapper });
    expect(result.current.locale).toBe("en");
  });

  it("does not crash when localStorage throws (privacy mode shim)", () => {
    const orig = Storage.prototype.getItem;
    Storage.prototype.getItem = () => {
      throw new Error("denied");
    };
    try {
      const { result } = renderHook(() => useI18n(), { wrapper });
      expect(result.current.locale).toBe("en");
    } finally {
      Storage.prototype.getItem = orig;
    }
  });
});

describe("useI18n outside provider", () => {
  it("returns a default value with locale=en and a no-op setLocale", () => {
    const { result } = renderHook(() => useI18n());
    expect(result.current.locale).toBe("en");
    expect(typeof result.current.setLocale).toBe("function");
    // Calling the no-op should not throw.
    expect(() => result.current.setLocale("ja")).not.toThrow();
  });
});

describe("setLocale", () => {
  it("updates the active locale and t bundle", () => {
    const { result } = renderHook(() => useI18n(), { wrapper });
    expect(result.current.locale).toBe("en");
    act(() => result.current.setLocale("zh"));
    expect(result.current.locale).toBe("zh");
    // Re-reads should return the new bundle.
    expect(result.current.t).toBeDefined();
  });

  it("persists the new locale to localStorage", () => {
    const { result } = renderHook(() => useI18n(), { wrapper });
    act(() => result.current.setLocale("de"));
    expect(localStorage.getItem("hermes-locale")).toBe("de");
  });

  it("swallows localStorage write errors silently", () => {
    const orig = Storage.prototype.setItem;
    Storage.prototype.setItem = () => {
      throw new Error("denied");
    };
    try {
      const { result } = renderHook(() => useI18n(), { wrapper });
      expect(() => act(() => result.current.setLocale("fr"))).not.toThrow();
      expect(result.current.locale).toBe("fr");
    } finally {
      Storage.prototype.setItem = orig;
    }
  });
});

describe("LOCALE_META", () => {
  it("contains entries for every supported locale", () => {
    for (const locale of [
      "en", "zh", "zh-hant", "ja", "de", "es", "fr", "tr",
      "uk", "af", "ko", "it", "ga", "pt", "ru", "hu",
    ]) {
      expect(LOCALE_META[locale as keyof typeof LOCALE_META]).toBeDefined();
    }
  });

  it("every entry has a name and a flag", () => {
    for (const meta of Object.values(LOCALE_META)) {
      expect(typeof meta.name).toBe("string");
      expect(meta.name.length).toBeGreaterThan(0);
      expect(typeof meta.flag).toBe("string");
      expect(meta.flag.length).toBeGreaterThan(0);
    }
  });
});

describe("I18nProvider wrapping a child component", () => {
  it("renders children and exposes the context to nested consumers", () => {
    function Inner() {
      const { locale } = useI18n();
      return <div data-testid="locale">{locale}</div>;
    }
    const { getByTestId } = render(
      <I18nProvider>
        <Inner />
      </I18nProvider>,
    );
    expect(getByTestId("locale").textContent).toBe("en");
  });
});
