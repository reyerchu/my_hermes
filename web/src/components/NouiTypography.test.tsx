import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { Typography } from "./NouiTypography";

describe("Typography", () => {
  it("renders a span by default with the provided children", () => {
    const { container } = render(<Typography>hello</Typography>);
    expect(container.firstChild?.nodeName).toBe("SPAN");
    expect(container.textContent).toBe("hello");
  });

  it("renders as a custom element when 'as' is provided", () => {
    const { container } = render(<Typography as="h2">heading</Typography>);
    expect(container.firstChild?.nodeName).toBe("H2");
  });

  it("applies the requested variant size class", () => {
    const { container } = render(<Typography variant="xl">big</Typography>);
    const el = container.firstChild as HTMLElement;
    expect(el.className).toMatch(/text-\[4\.5rem\]/);
  });

  it("merges caller-provided className with internal classes", () => {
    const { container } = render(
      <Typography className="custom-class">x</Typography>,
    );
    const el = container.firstChild as HTMLElement;
    expect(el.className).toMatch(/custom-class/);
  });

  it("forwards extra props onto the underlying element", () => {
    const { container } = render(
      <Typography data-testid="t1" id="my-id">
        x
      </Typography>,
    );
    const el = container.firstChild as HTMLElement;
    expect(el.id).toBe("my-id");
    expect(el.getAttribute("data-testid")).toBe("t1");
  });

  it("applies the courier modifier class when courier is true", () => {
    const { container } = render(<Typography courier>x</Typography>);
    const el = container.firstChild as HTMLElement;
    expect(el.className).toMatch(/courier|font-courier/i);
  });
});
