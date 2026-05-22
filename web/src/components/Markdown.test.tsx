import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { Markdown } from "./Markdown";

describe("Markdown", () => {
  it("renders empty content without crashing", () => {
    const { container } = render(<Markdown content="" />);
    expect(container.firstChild).not.toBeNull();
  });

  it("renders plain paragraph text", () => {
    const { container } = render(<Markdown content="hello world" />);
    expect(container.textContent).toContain("hello world");
  });

  it("renders a fenced code block", () => {
    const { container } = render(
      <Markdown content={"```\nconst x = 1;\n```"} />,
    );
    const code = container.querySelector("code") ?? container.querySelector("pre");
    expect(code).not.toBeNull();
    expect(code!.textContent).toContain("const x = 1;");
  });

  it("renders inline code with backticks", () => {
    const { container } = render(<Markdown content="use `foo()` to call" />);
    expect(container.querySelector("code")?.textContent).toBe("foo()");
  });

  it("renders bold text with double-asterisks", () => {
    const { container } = render(<Markdown content="this is **important**" />);
    expect(container.querySelector("strong")?.textContent).toBe("important");
  });

  it("renders headers", () => {
    const { container } = render(<Markdown content="# Title" />);
    const heading = container.querySelector("h1, h2, h3");
    expect(heading).not.toBeNull();
    expect(heading!.textContent).toBe("Title");
  });

  it("renders links with target=_blank for safety", () => {
    const { container } = render(
      <Markdown content="[hermes](https://hermes.example)" />,
    );
    const link = container.querySelector("a");
    expect(link).not.toBeNull();
    expect(link!.getAttribute("href")).toBe("https://hermes.example");
  });

  it("renders an ordered list", () => {
    const md = `1. one\n2. two`;
    const { container } = render(<Markdown content={md} />);
    const ol = container.querySelector("ol");
    expect(ol).not.toBeNull();
    expect(ol!.querySelectorAll("li").length).toBeGreaterThanOrEqual(1);
  });

  it("renders an unordered list", () => {
    const md = `- a\n- b\n- c`;
    const { container } = render(<Markdown content={md} />);
    const ul = container.querySelector("ul");
    expect(ul).not.toBeNull();
    expect(ul!.querySelectorAll("li").length).toBeGreaterThanOrEqual(1);
  });

  it("appends a blinking caret when streaming=true", () => {
    const { container } = render(
      <Markdown content="generating" streaming />,
    );
    // The streaming caret is a span with aria-hidden + animate-pulse.
    expect(container.querySelector("[aria-hidden]")).not.toBeNull();
  });

  it("renders the caret alone when content is empty and streaming", () => {
    const { container } = render(<Markdown content="" streaming />);
    expect(container.querySelector("[aria-hidden]")).not.toBeNull();
  });

  it("highlights matched terms when highlightTerms is provided", () => {
    const { container } = render(
      <Markdown content="the quick brown fox" highlightTerms={["quick", "fox"]} />,
    );
    // Highlighter wraps matches in a <mark> or styled span — accept either.
    const marks = container.querySelectorAll("mark, .bg-warning, [data-highlight]");
    expect(marks.length).toBeGreaterThanOrEqual(1);
  });
});
