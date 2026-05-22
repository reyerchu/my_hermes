import { describe, it, expect, vi, afterEach } from "vitest";
import { render, fireEvent, cleanup } from "@testing-library/react";

vi.mock("@nous-research/ui/ui/components/list-item", () => ({
  ListItem: ({ children, onClick }: any) => (
    <div onClick={onClick} role="listitem">{children}</div>
  ),
}));

import { ToolCall, type ToolEntry } from "./ToolCall";

function makeTool(over: Partial<ToolEntry> = {}): ToolEntry {
  return {
    kind: "tool",
    id: "t1",
    tool_id: "tool-1",
    name: "read_file",
    context: "path=/foo",
    status: "done",
    startedAt: Date.now() - 1500,
    completedAt: Date.now(),
    ...over,
  };
}

afterEach(() => cleanup());

describe("ToolCall", () => {
  it("renders the tool name", () => {
    const { container } = render(<ToolCall tool={makeTool()} />);
    expect(container.textContent).toContain("read_file");
  });

  it("renders the context inline next to the name", () => {
    const { container } = render(
      <ToolCall tool={makeTool({ context: "path=/foo" })} />,
    );
    expect(container.textContent).toContain("path=/foo");
  });

  it("starts collapsed for completed tools", () => {
    const { container } = render(
      <ToolCall tool={makeTool({ summary: "ok" })} />,
    );
    expect(container.textContent).not.toContain("ok");
  });

  it("auto-expands when the tool errored", () => {
    const { container } = render(
      <ToolCall
        tool={makeTool({ status: "error", error: "EACCES" })}
      />,
    );
    expect(container.textContent).toContain("EACCES");
  });

  it("clicking the header toggles expansion", () => {
    const { container } = render(
      <ToolCall tool={makeTool({ summary: "result body" })} />,
    );
    expect(container.textContent).not.toContain("result body");
    const header = container.querySelector("[role='listitem']") as HTMLElement;
    fireEvent.click(header);
    expect(container.textContent).toContain("result body");
  });

  it("shows the preview body while running", () => {
    const { container } = render(
      <ToolCall
        tool={makeTool({
          status: "running",
          completedAt: undefined,
          preview: "streaming output…",
        })}
      />,
    );
    // Running tools also start collapsed; click to reveal.
    const header = container.querySelector("[role='listitem']") as HTMLElement;
    fireEvent.click(header);
    expect(container.textContent).toContain("streaming output");
  });

  it("formats elapsed time using s/m/h units", () => {
    const now = Date.now();
    const { container } = render(
      <ToolCall
        tool={makeTool({ startedAt: now - 3500, completedAt: now })}
      />,
    );
    // Either "3.5s" or "4s" depending on rounding; both contain "s".
    expect(container.textContent).toMatch(/\d+(\.\d)?s/);
  });

  it("renders an inline_diff section when provided", () => {
    const { container } = render(
      <ToolCall
        tool={makeTool({
          summary: "applied",
          inline_diff: "+ added line\n- removed line",
        })}
      />,
    );
    const header = container.querySelector("[role='listitem']") as HTMLElement;
    fireEvent.click(header);
    expect(container.textContent).toContain("added line");
    expect(container.textContent).toContain("removed line");
  });
});
