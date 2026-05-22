import { describe, it, expect, vi } from "vitest";
import { render, cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

vi.mock("@/i18n", () => ({
  useI18n: () => ({
    t: {
      status: {
        connected: "connected",
        disconnected: "disconnected",
        error: "error",
        connectedPlatforms: "Connected Platforms",
        lastSeen: "last seen",
      },
    },
  }),
}));
vi.mock("@nous-research/ui/ui/components/badge", () => ({
  Badge: ({ children }: any) => <span>{children}</span>,
}));

import { PlatformsCard } from "./PlatformsCard";

afterEach(() => cleanup());

describe("PlatformsCard", () => {
  it("renders the section title", () => {
    const { container } = render(<PlatformsCard platforms={[]} />);
    expect(container.textContent).toContain("Connected Platforms");
  });

  it("renders one row per platform tuple", () => {
    const platforms: Array<[string, any]> = [
      ["telegram", { state: "connected", last_seen: new Date().toISOString() }],
      ["discord", { state: "disconnected", last_seen: null }],
    ];
    const { container } = render(<PlatformsCard platforms={platforms} />);
    expect(container.textContent).toContain("telegram");
    expect(container.textContent).toContain("discord");
  });

  it("shows the 'connected' badge for a connected platform", () => {
    const { container } = render(
      <PlatformsCard
        platforms={[["telegram", { state: "connected", last_seen: null }]]}
      />,
    );
    expect(container.textContent).toContain("connected");
  });

  it("shows the 'error' badge for a fatal platform", () => {
    const { container } = render(
      <PlatformsCard
        platforms={[["slack", { state: "fatal", last_seen: null }]]}
      />,
    );
    expect(container.textContent).toContain("error");
  });

  it("falls back to the raw state string for an unknown badge", () => {
    const { container } = render(
      <PlatformsCard
        platforms={[
          ["x", { state: "rebooting" as any, last_seen: null }],
        ]}
      />,
    );
    expect(container.textContent).toContain("rebooting");
  });
});
