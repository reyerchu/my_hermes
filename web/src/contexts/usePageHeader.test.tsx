import { describe, it, expect, vi } from "vitest";
import { act, render, renderHook } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { usePageHeader } from "./usePageHeader";
import { PageHeaderProvider } from "./PageHeaderProvider";

// useI18n is used by PageHeaderProvider to compute default titles.  Provide a
// minimal stub so we don't drag in the real translation table for unit tests.
vi.mock("@/i18n", () => ({
  useI18n: () => ({
    t: {
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
    },
  }),
}));

describe("usePageHeader (outside provider)", () => {
  it("throws a helpful error when used without provider", () => {
    expect(() => renderHook(() => usePageHeader())).toThrow(
      /must be used within a PageHeaderProvider/,
    );
  });
});

describe("PageHeaderProvider", () => {
  function Wrapper({
    children,
    initialEntries = ["/chat"],
  }: {
    children: React.ReactNode;
    initialEntries?: string[];
  }) {
    return (
      <MemoryRouter initialEntries={initialEntries}>
        <PageHeaderProvider pluginTabs={[]}>{children}</PageHeaderProvider>
      </MemoryRouter>
    );
  }

  it("renders default title from the current route", () => {
    const { container } = render(
      <Wrapper initialEntries={["/sessions"]}>
        <div>content</div>
      </Wrapper>,
    );
    expect(container.querySelector("h1")?.textContent).toBe("Sessions");
  });

  it("exposes a context with setter callbacks", () => {
    const { result } = renderHook(() => usePageHeader(), {
      wrapper: ({ children }: { children: React.ReactNode }) => (
        <Wrapper>{children}</Wrapper>
      ),
    });
    expect(typeof result.current.setTitle).toBe("function");
    expect(typeof result.current.setAfterTitle).toBe("function");
    expect(typeof result.current.setEnd).toBe("function");
  });

  it("setTitle override replaces the default page title", () => {
    function Inner() {
      const { setTitle } = usePageHeader();
      return (
        <button type="button" onClick={() => setTitle("Custom")}>
          go
        </button>
      );
    }
    const { container, getByRole } = render(
      <Wrapper initialEntries={["/sessions"]}>
        <Inner />
      </Wrapper>,
    );
    expect(container.querySelector("h1")?.textContent).toBe("Sessions");
    act(() => getByRole("button").click());
    expect(container.querySelector("h1")?.textContent).toBe("Custom");
  });

  it("renders a plugin-tab label when its path matches", () => {
    const plugin = [{ path: "/plugins/kanban", label: "Kanban Board" }];
    function W({ children }: { children: React.ReactNode }) {
      return (
        <MemoryRouter initialEntries={["/plugins/kanban"]}>
          <PageHeaderProvider pluginTabs={plugin}>{children}</PageHeaderProvider>
        </MemoryRouter>
      );
    }
    const { container } = render(
      <W>
        <div />
      </W>,
    );
    expect(container.querySelector("h1")?.textContent).toBe("Kanban Board");
  });
});
