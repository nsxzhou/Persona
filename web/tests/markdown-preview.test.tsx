import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { MarkdownPreview } from "@/components/markdown-preview";
import { MarkdownPreviewRenderer } from "@/components/markdown-preview-renderer";

describe("MarkdownPreview", () => {
  test("shows a stable fallback while the preview renderer loads", () => {
    render(<MarkdownPreview content={"# Title\n\n**bold**"} />);
    expect(screen.getByText("正在载入预览...")).toBeInTheDocument();
  });

  test("keeps empty content lightweight", () => {
    render(<MarkdownPreview content="" />);
    expect(screen.getByText("(empty)")).toBeInTheDocument();
  });
});

describe("MarkdownPreviewRenderer", () => {
  test("renders markdown content", () => {
    render(<MarkdownPreviewRenderer content={"# Title\n\n**bold**"} />);
    expect(screen.getByText("Title")).toBeInTheDocument();
    expect(screen.getByText("bold")).toBeInTheDocument();
  });

  test("does not render dangerous iframe tag (sanitized)", () => {
    render(
      <MarkdownPreviewRenderer
        content={'# x\n\n<IFRAME SRC="javascript:alert(window.origin)"></IFRAME>\n'}
      />,
    );
    expect(screen.getByText("x")).toBeInTheDocument();
    expect(document.querySelector("iframe")).toBeNull();
  });
});
