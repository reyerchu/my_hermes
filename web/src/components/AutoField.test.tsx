import { describe, it, expect, vi, afterEach } from "vitest";
import { render, fireEvent, cleanup } from "@testing-library/react";

afterEach(() => cleanup());

vi.mock("@nous-research/ui/ui/components/select", () => ({
  Select: ({ children, value, onValueChange }: any) => (
    <select
      data-testid="select"
      value={value}
      onChange={(e) => onValueChange?.(e.target.value)}
    >
      {children}
    </select>
  ),
  SelectOption: ({ value, children }: any) => <option value={value}>{children}</option>,
}));
vi.mock("@nous-research/ui/ui/components/switch", () => ({
  Switch: ({ checked, onCheckedChange }: any) => (
    <input
      role="switch"
      type="checkbox"
      checked={checked}
      onChange={(e) => onCheckedChange?.(e.target.checked)}
    />
  ),
}));

import { AutoField } from "./AutoField";

describe("AutoField", () => {
  it("renders a Switch for boolean schema", () => {
    const onChange = vi.fn();
    const { getByRole } = render(
      <AutoField
        schemaKey="enabled"
        schema={{ type: "boolean" }}
        value={false}
        onChange={onChange}
      />,
    );
    expect(getByRole("switch")).toBeTruthy();
  });

  it("Switch onCheckedChange forwards to onChange", () => {
    const onChange = vi.fn();
    const { getByRole } = render(
      <AutoField
        schemaKey="enabled"
        schema={{ type: "boolean" }}
        value={false}
        onChange={onChange}
      />,
    );
    fireEvent.click(getByRole("switch"));
    expect(onChange).toHaveBeenCalledWith(true);
  });

  it("renders a Select for select schema with options", () => {
    const { getByTestId } = render(
      <AutoField
        schemaKey="model"
        schema={{ type: "select", options: ["opus", "sonnet", "haiku"] }}
        value="sonnet"
        onChange={() => {}}
      />,
    );
    const select = getByTestId("select") as HTMLSelectElement;
    expect(select.value).toBe("sonnet");
    expect(select.querySelectorAll("option")).toHaveLength(3);
  });

  it("Select forwards changed value via onChange", () => {
    const onChange = vi.fn();
    const { getByTestId } = render(
      <AutoField
        schemaKey="model"
        schema={{ type: "select", options: ["opus", "sonnet"] }}
        value="opus"
        onChange={onChange}
      />,
    );
    fireEvent.change(getByTestId("select"), { target: { value: "sonnet" } });
    expect(onChange).toHaveBeenCalledWith("sonnet");
  });

  it("renders a text Input for unknown schema types", () => {
    const { container } = render(
      <AutoField
        schemaKey="name"
        schema={{ type: "string" }}
        value="hello"
        onChange={() => {}}
      />,
    );
    const input = container.querySelector("input[type='text']") ??
      container.querySelector("input");
    expect(input).not.toBeNull();
  });

  it("humanises the rendered label (snake_case → Title Case)", () => {
    const { container } = render(
      <AutoField
        schemaKey="busy_input_mode"
        schema={{ type: "boolean" }}
        value={false}
        onChange={() => {}}
      />,
    );
    expect(container.textContent).toContain("Busy Input Mode");
  });

  it("uses the last dotted segment as the label and shows the key path hint", () => {
    const { container } = render(
      <AutoField
        schemaKey="display.busy_input_mode"
        schema={{ type: "boolean", description: "How busy input behaves" }}
        value={false}
        onChange={() => {}}
      />,
    );
    expect(container.textContent).toContain("Busy Input Mode");
    expect(container.textContent).toContain("display.busy_input_mode");
    expect(container.textContent).toContain("How busy input behaves");
  });
});
