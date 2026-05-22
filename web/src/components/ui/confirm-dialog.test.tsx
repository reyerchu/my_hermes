import { describe, it, expect, vi, afterEach } from "vitest";
import { render, fireEvent, cleanup } from "@testing-library/react";
import { ConfirmDialog } from "./confirm-dialog";

// ConfirmDialog imports a Button from @nous-research/ui which pulls in a
// dist/utils directory that breaks ESM resolution under jsdom — stub it.
vi.mock("@nous-research/ui/ui/components/button", () => ({
  Button: ({ children, onClick, disabled, ...rest }: any) => (
    <button onClick={onClick} disabled={disabled} {...rest}>{children}</button>
  ),
}));

describe("ConfirmDialog", () => {
  afterEach(() => {
    cleanup();
    document.body.style.overflow = "";
  });

  it("renders nothing when open is false", () => {
    const { container } = render(
      <ConfirmDialog
        open={false}
        onConfirm={() => {}}
        onCancel={() => {}}
        title="Delete?"
      />,
    );
    expect(container.firstChild).toBeNull();
    expect(document.body.querySelector('[role="dialog"]')).toBeNull();
  });

  it("renders into a portal with role=dialog and aria-modal when open", () => {
    render(
      <ConfirmDialog
        open
        onConfirm={() => {}}
        onCancel={() => {}}
        title="Delete?"
      />,
    );
    const dlg = document.body.querySelector('[role="dialog"]');
    expect(dlg).not.toBeNull();
    expect(dlg!.getAttribute("aria-modal")).toBe("true");
  });

  it("invokes onConfirm when the confirm button is clicked", () => {
    const onConfirm = vi.fn();
    render(
      <ConfirmDialog
        open
        onConfirm={onConfirm}
        onCancel={() => {}}
        title="Delete?"
        confirmLabel="Yes"
      />,
    );
    const btn = document.body.querySelector('[data-confirm]') as HTMLButtonElement;
    expect(btn).not.toBeNull();
    btn.click();
    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it("invokes onCancel when Escape is pressed", () => {
    const onCancel = vi.fn();
    render(
      <ConfirmDialog
        open
        onConfirm={() => {}}
        onCancel={onCancel}
        title="Delete?"
      />,
    );
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("invokes onCancel when the backdrop is clicked", () => {
    const onCancel = vi.fn();
    render(
      <ConfirmDialog
        open
        onConfirm={() => {}}
        onCancel={onCancel}
        title="Delete?"
      />,
    );
    const dlg = document.body.querySelector('[role="dialog"]') as HTMLElement;
    // The backdrop is the role=dialog div itself; click target === currentTarget.
    fireEvent.click(dlg, { target: dlg });
    expect(onCancel).toHaveBeenCalled();
  });

  it("locks body scroll while open and restores it on close", () => {
    document.body.style.overflow = "auto";
    const { rerender } = render(
      <ConfirmDialog open onConfirm={() => {}} onCancel={() => {}} title="t" />,
    );
    expect(document.body.style.overflow).toBe("hidden");
    rerender(
      <ConfirmDialog
        open={false}
        onConfirm={() => {}}
        onCancel={() => {}}
        title="t"
      />,
    );
    expect(document.body.style.overflow).toBe("auto");
  });

  it("shows the destructive variant when destructive is true", () => {
    render(
      <ConfirmDialog
        open
        destructive
        onConfirm={() => {}}
        onCancel={() => {}}
        title="Delete?"
      />,
    );
    // Destructive variant injects an AlertTriangle SVG into the header — its
    // presence is the cheapest proxy for the destructive prop.
    expect(document.body.querySelector("svg")).not.toBeNull();
  });
});
