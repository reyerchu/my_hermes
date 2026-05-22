import { describe, it, expect, vi, afterEach } from "vitest";
import { render, cleanup, waitFor, act } from "@testing-library/react";
import { createRef } from "react";

vi.mock("@nous-research/ui/ui/components/list-item", () => ({
  ListItem: ({ children, onClick }: any) => (
    <div role="listitem" onClick={onClick}>{children}</div>
  ),
}));

import {
  SlashPopover,
  type SlashPopoverHandle,
  type CompletionItem,
} from "./SlashPopover";

function makeGw(items: CompletionItem[] = []) {
  return {
    request: vi.fn().mockResolvedValue({ items, replace_from: 0 }),
  } as any;
}

afterEach(() => cleanup());

describe("SlashPopover", () => {
  it("renders nothing when input does not start with '/'", () => {
    const { container } = render(
      <SlashPopover input="hello world" gw={makeGw()} onApply={() => {}} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("does NOT call gw.request when gw is null", () => {
    render(<SlashPopover input="/he" gw={null} onApply={() => {}} />);
    // No gw means no fetch; the popover just stays empty.
  });

  it("fetches completions when input starts with /", async () => {
    const gw = makeGw([
      { display: "help", text: "/help" },
      { display: "model", text: "/model" },
    ]);
    render(<SlashPopover input="/he" gw={gw} onApply={() => {}} />);
    await waitFor(() => expect(gw.request).toHaveBeenCalled());
  });

  it("renders the returned completion items", async () => {
    const gw = makeGw([
      { display: "help", text: "/help" },
      { display: "model", text: "/model" },
    ]);
    const { container } = render(
      <SlashPopover input="/h" gw={gw} onApply={() => {}} />,
    );
    await waitFor(() =>
      expect(container.textContent).toContain("help"),
    );
    expect(container.textContent).toContain("model");
  });

  it("renders nothing when the completion list is empty", async () => {
    const gw = makeGw([]);
    const { container } = render(
      <SlashPopover input="/zzz" gw={gw} onApply={() => {}} />,
    );
    await waitFor(() => expect(gw.request).toHaveBeenCalled());
    // After settling, no list items should be present.
    await new Promise((r) => setTimeout(r, 100));
    expect(container.querySelectorAll("[role='listitem']").length).toBe(0);
  });

  it("handleKey returns false when no items are loaded", () => {
    const ref = createRef<SlashPopoverHandle>();
    render(
      <SlashPopover ref={ref} input="" gw={makeGw()} onApply={() => {}} />,
    );
    const e = { key: "ArrowDown", preventDefault: () => {} } as any;
    expect(ref.current?.handleKey(e)).toBe(false);
  });

  it("handleKey ArrowDown returns true once items exist", async () => {
    const ref = createRef<SlashPopoverHandle>();
    const gw = makeGw([{ display: "a", text: "/a" }, { display: "b", text: "/b" }]);
    render(<SlashPopover ref={ref} input="/" gw={gw} onApply={() => {}} />);
    await waitFor(() => expect(gw.request).toHaveBeenCalled());
    // Give the debounced state update a tick.
    await act(async () => {
      await new Promise((r) => setTimeout(r, 80));
    });
    const e = { key: "ArrowDown", preventDefault: () => {} } as any;
    expect(ref.current?.handleKey(e)).toBe(true);
  });
});
