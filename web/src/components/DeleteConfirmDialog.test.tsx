import { describe, it, expect, vi } from "vitest";
import { render, cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

vi.mock("@/i18n", () => ({
  useI18n: () => ({
    t: { common: { delete: "Delete", cancel: "Cancel" } },
  }),
}));
vi.mock("@nous-research/ui/ui/components/button", () => ({
  Button: ({ children, onClick, disabled, ...rest }: any) => (
    <button onClick={onClick} disabled={disabled} {...rest}>{children}</button>
  ),
}));

import { DeleteConfirmDialog } from "./DeleteConfirmDialog";

afterEach(() => {
  cleanup();
  document.body.style.overflow = "";
});

describe("DeleteConfirmDialog", () => {
  it("renders nothing when closed", () => {
    const { container } = render(
      <DeleteConfirmDialog
        open={false}
        loading={false}
        onConfirm={() => {}}
        onCancel={() => {}}
        title="Delete this?"
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders a destructive dialog when open", () => {
    render(
      <DeleteConfirmDialog
        open
        loading={false}
        onConfirm={() => {}}
        onCancel={() => {}}
        title="Delete account"
      />,
    );
    const dlg = document.body.querySelector('[role="dialog"]');
    expect(dlg).not.toBeNull();
    expect(dlg!.textContent).toContain("Delete account");
  });

  it("default confirm label comes from i18n.common.delete", () => {
    render(
      <DeleteConfirmDialog
        open
        loading={false}
        onConfirm={() => {}}
        onCancel={() => {}}
        title="t"
      />,
    );
    const confirm = document.body.querySelector('[data-confirm]');
    expect(confirm!.textContent).toBe("Delete");
  });

  it("custom labels override i18n defaults", () => {
    render(
      <DeleteConfirmDialog
        open
        loading={false}
        onConfirm={() => {}}
        onCancel={() => {}}
        title="t"
        confirmLabel="Yes, nuke it"
        cancelLabel="Abort"
      />,
    );
    expect(document.body.textContent).toContain("Yes, nuke it");
    expect(document.body.textContent).toContain("Abort");
  });

  it("invokes onConfirm when the confirm button is clicked", () => {
    const onConfirm = vi.fn();
    render(
      <DeleteConfirmDialog
        open
        loading={false}
        onConfirm={onConfirm}
        onCancel={() => {}}
        title="t"
      />,
    );
    (document.body.querySelector('[data-confirm]') as HTMLButtonElement).click();
    expect(onConfirm).toHaveBeenCalledOnce();
  });
});
