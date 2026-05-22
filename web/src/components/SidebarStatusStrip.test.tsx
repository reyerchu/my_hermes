import { describe, it, expect, vi, beforeEach } from "vitest";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

const statusValue = { value: null as any };
vi.mock("@/hooks/useSidebarStatus", () => ({
  useSidebarStatus: () => statusValue.value,
}));
vi.mock("@/i18n", () => ({
  useI18n: () => ({
    t: {
      app: {
        statusOverview: "Overview",
        activeSessionsLabel: "Active",
        gatewayStatusLabel: "Gateway",
        gatewayStrip: {
          running: "running",
          starting: "starting",
          failed: "failed",
          stopped: "stopped",
          off: "off",
        },
      },
    },
  }),
}));

import { SidebarStatusStrip } from "./SidebarStatusStrip";

function wrap(node: React.ReactNode) {
  return <MemoryRouter>{node}</MemoryRouter>;
}

describe("SidebarStatusStrip", () => {
  beforeEach(() => {
    statusValue.value = null;
  });

  it("renders a placeholder skeleton while status is null", () => {
    const { container } = render(wrap(<SidebarStatusStrip />));
    // A pulsing div with aria-hidden is the loading placeholder.
    expect(container.querySelector("[aria-hidden]")).not.toBeNull();
  });

  it("renders a /sessions Link once status is loaded", () => {
    statusValue.value = {
      gateway_running: true,
      gateway_state: "running",
      sessions: { active: 0 },
    };
    const { container } = render(wrap(<SidebarStatusStrip />));
    const link = container.querySelector("a");
    expect(link).not.toBeNull();
    expect(link!.getAttribute("href")).toBe("/sessions");
  });

  it("includes the gateway status label and value", () => {
    statusValue.value = {
      gateway_running: true,
      gateway_state: "running",
      sessions: { active: 0 },
    };
    const { container } = render(wrap(<SidebarStatusStrip />));
    expect(container.textContent).toContain("Gateway");
  });

  it("includes the active sessions label and count", () => {
    statusValue.value = {
      gateway_running: true,
      gateway_state: "running",
      active_sessions: 7,
    };
    const { container } = render(wrap(<SidebarStatusStrip />));
    expect(container.textContent).toContain("Active");
    expect(container.textContent).toContain("7");
  });
});
