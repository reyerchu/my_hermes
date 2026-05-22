/**
 * Coverage for the small shadcn-style ui primitives that the rest of the
 * app composes against.  Each is a thin wrapper around a native DOM
 * element with a few defaulted classes; the tests assert the public
 * contract (semantics, class merging, prop forwarding) so a refactor
 * that breaks any of those gets flagged.
 */
import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "./card";
import { Checkbox } from "./checkbox";
import { Input } from "./input";
import { Label } from "./label";
import { Separator } from "./separator";

describe("Card family", () => {
  it("renders a Card div containing children", () => {
    const { container } = render(<Card>card body</Card>);
    const el = container.firstChild as HTMLElement;
    expect(el.nodeName).toBe("DIV");
    expect(el.textContent).toBe("card body");
  });

  it("Card merges caller className with defaults", () => {
    const { container } = render(<Card className="extra-class" />);
    expect((container.firstChild as HTMLElement).className).toMatch(
      /extra-class/,
    );
  });

  it("Card forwards style overrides on top of the themed defaults", () => {
    const { container } = render(<Card style={{ color: "red" }} />);
    expect((container.firstChild as HTMLElement).style.color).toBe("red");
  });

  it("CardHeader renders a div with the bordered layout", () => {
    const { container } = render(<CardHeader />);
    expect((container.firstChild as HTMLElement).className).toMatch(
      /border-b/,
    );
  });

  it("CardTitle renders an h3 with the expanded font class", () => {
    const { container } = render(<CardTitle>title</CardTitle>);
    expect(container.firstChild?.nodeName).toBe("H3");
    expect((container.firstChild as HTMLElement).className).toMatch(
      /font-expanded/,
    );
  });

  it("CardDescription renders a p", () => {
    const { container } = render(<CardDescription>desc</CardDescription>);
    expect(container.firstChild?.nodeName).toBe("P");
  });

  it("CardContent renders a div with padding", () => {
    const { container } = render(<CardContent>body</CardContent>);
    const el = container.firstChild as HTMLElement;
    expect(el.nodeName).toBe("DIV");
    expect(el.className).toMatch(/p-4/);
  });
});

describe("Checkbox", () => {
  it("renders an input type=checkbox", () => {
    const { container } = render(<Checkbox />);
    const el = container.querySelector("input");
    expect(el).not.toBeNull();
    expect(el!.type).toBe("checkbox");
  });

  it("forwards checked + onChange to the native input", () => {
    let changed = false;
    const { container } = render(
      <Checkbox checked onChange={() => (changed = true)} />,
    );
    const el = container.querySelector("input") as HTMLInputElement;
    expect(el.checked).toBe(true);
    el.click();
    expect(changed).toBe(true);
  });
});

describe("Input", () => {
  it("renders a native input element", () => {
    const { container } = render(<Input />);
    expect(container.querySelector("input")).not.toBeNull();
  });

  it("forwards the placeholder prop", () => {
    const { container } = render(<Input placeholder="search…" />);
    expect(container.querySelector("input")!.placeholder).toBe("search…");
  });

  it("merges caller className with the defaults", () => {
    const { container } = render(<Input className="custom-input" />);
    expect(container.querySelector("input")!.className).toMatch(
      /custom-input/,
    );
  });
});

describe("Label", () => {
  it("renders a native label element with default classes", () => {
    const { container } = render(<Label>name</Label>);
    const el = container.firstChild as HTMLElement;
    expect(el.nodeName).toBe("LABEL");
    expect(el.className).toMatch(/font-mondwest/);
  });

  it("forwards htmlFor to support associating with an input", () => {
    const { container } = render(<Label htmlFor="email">email</Label>);
    expect((container.firstChild as HTMLLabelElement).htmlFor).toBe("email");
  });
});

describe("Separator", () => {
  it("renders with role=separator", () => {
    const { container } = render(<Separator />);
    expect((container.firstChild as HTMLElement).getAttribute("role")).toBe(
      "separator",
    );
  });

  it("horizontal (default) gets h-px", () => {
    const { container } = render(<Separator />);
    expect((container.firstChild as HTMLElement).className).toMatch(/h-px/);
  });

  it("vertical gets w-px", () => {
    const { container } = render(<Separator orientation="vertical" />);
    expect((container.firstChild as HTMLElement).className).toMatch(/w-px/);
  });

  it("forwards extra props onto the underlying element", () => {
    const { container } = render(<Separator data-testid="sep" />);
    expect(
      (container.firstChild as HTMLElement).getAttribute("data-testid"),
    ).toBe("sep");
  });
});
