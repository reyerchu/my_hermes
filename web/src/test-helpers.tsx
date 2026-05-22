/**
 * Shared scaffolding for page-level component tests.
 *
 * Pages tend to pull in `useI18n`, `usePageHeader`, the router, and
 * `@/lib/api`.  Centralising the stubs here keeps each page test focused
 * on its own behavior instead of repeating ten lines of `vi.mock(...)`
 * boilerplate.  Keep this file dependency-free of anything that touches
 * the network or design-language internals.
 */
import { vi } from "vitest";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";

/** Build a minimal Translations stub that pages can read. */
export const stubT = {
  app: {
    webUi: "Hermes Web",
    openDocumentation: "Open Documentation",
    statusOverview: "Status",
    activeSessionsLabel: "Active",
    gatewayStatusLabel: "Gateway",
    nav: {
      chat: "Chat",
      sessions: "Sessions",
      analytics: "Analytics",
      models: "Models",
      logs: "Logs",
      cron: "Cron",
      skills: "Skills",
      plugins: "Plugins",
      profiles: "Profiles",
      config: "Config",
      keys: "Env Keys",
      documentation: "Docs",
    },
  },
  common: {
    cancel: "Cancel",
    delete: "Delete",
    save: "Save",
    edit: "Edit",
    add: "Add",
    close: "Close",
    confirm: "Confirm",
  },
  status: {
    actionFinished: "Action finished",
    actionFailed: "Action failed",
  },
};

/**
 * Wrap children in a MemoryRouter at the requested route.  Page tests
 * that only need routing context (not a real PageHeaderProvider) use
 * this.  Tests that want both should compose with PageHeaderProvider
 * directly.
 */
export function RouterWrapper({
  children,
  initialEntries = ["/"],
}: {
  children: ReactNode;
  initialEntries?: string[];
}) {
  return <MemoryRouter initialEntries={initialEntries}>{children}</MemoryRouter>;
}

/**
 * Page tests need a usable usePageHeader context that records calls
 * without rendering the full header chrome.  Returns spies the test
 * can assert against.
 */
export function makePageHeaderStub() {
  return {
    setTitle: vi.fn(),
    setAfterTitle: vi.fn(),
    setEnd: vi.fn(),
  };
}

/**
 * Build a recursive translation Proxy that returns the dotted key path as
 * the string value for any access.  Used by page tests so they don't have
 * to enumerate every `t.section.key` the page might read — placeholders
 * like `"{count}"` survive because `.replace()` honours the synthetic
 * string's own semantics.  React's "Functions are not valid as a React
 * child" warnings under jsdom are cosmetic and do not affect test outcomes.
 */
export function makeTranslationStub(path: string[] = []): any {
  return new Proxy(() => path.join("."), {
    get(_, prop: string) {
      if (prop === Symbol.toPrimitive) return () => path.join(".");
      if (prop === "toString") return () => path.join(".") || "_";
      if (prop === "replace") {
        const asString = path.join(".") || "_";
        return (...args: Parameters<string["replace"]>) =>
          asString.replace(...args);
      }
      // Pages occasionally treat translation values as React elements via
      // dangerouslySet props — surface a primitive when truthy-coerced.
      if (prop === "valueOf") return () => path.join(".") || "_";
      return makeTranslationStub([...path, prop]);
    },
  });
}
