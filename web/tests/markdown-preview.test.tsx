import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { MarkdownPreview } from "@/components/markdown-preview";

describe("MarkdownPreview", () => {
  test("renders markdown content", () => {
    render(<MarkdownPreview content={"# Title\n\n**bold**"} />);
    expect(screen.getByText("Title")).toBeInTheDocument();
    expect(screen.getByText("bold")).toBeInTheDocument();
  });

  test("does not render dangerous iframe tag (sanitized)", () => {
    render(
      <MarkdownPreview
        content={'# x\n\n<IFRAME SRC="javascript:alert(window.origin)"></IFRAME>\n'}
      />,
    );
    expect(document.querySelector("iframe")).toBeNull();
  });
});
