import { describe, it, expect } from "vitest";
import { resolvePageTitle } from "./resolve-page-title";
import type { Translations } from "@/i18n/types";

// Minimal Translations stub — only the keys the resolver reads.
const t = {
  app: {
    webUi: "Hermes Web",
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
} as unknown as Translations;

describe("resolvePageTitle", () => {
  it("returns the Sessions label for the root path", () => {
    expect(resolvePageTitle("/", t, [])).toBe("Sessions");
  });

  it("resolves a built-in chat path", () => {
    expect(resolvePageTitle("/chat", t, [])).toBe("Chat");
  });

  it("resolves a built-in path with a trailing slash", () => {
    expect(resolvePageTitle("/chat/", t, [])).toBe("Chat");
  });

  it("maps /env to the env-keys label", () => {
    expect(resolvePageTitle("/env", t, [])).toBe("Env Keys");
  });

  it("prefers a plugin tab over the builtin fallback", () => {
    const tabs = [{ path: "/plugins/kanban", label: "Kanban" }];
    expect(resolvePageTitle("/plugins/kanban", t, tabs)).toBe("Kanban");
  });

  it("derives a title from an unknown segment by capitalising it", () => {
    expect(resolvePageTitle("/whatever", t, [])).toBe("Whatever");
  });

  it("returns the bare app label when there's no resolvable segment", () => {
    // After stripping trailing slash, empty segment falls through to default.
    expect(resolvePageTitle("", t, [])).toBe("Sessions");
  });

  it("plugin tabs match exact path, not prefixes", () => {
    const tabs = [{ path: "/plugins/kanban", label: "Kanban" }];
    // Sibling path should not pick up the kanban label.  Fallback
    // capitalises only the first char, so nested segments are preserved.
    expect(resolvePageTitle("/plugins/other", t, tabs)).toBe("Plugins/other");
  });
});
