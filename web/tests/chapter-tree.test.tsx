import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { ChapterTree } from "@/components/chapter-tree";
import type { ParsedOutline } from "@/lib/outline-parser";

function buildOutline(): ParsedOutline {
  return {
    volumes: [
      {
        title: "第一卷",
        meta: "",
        chapters: [
          {
            title: "第1章",
            coreEvent: "事件一",
            emotionArc: "情绪一",
            chapterHook: "钩子一",
            rawMarkdown: "raw",
          },
          {
            title: "第2章",
            coreEvent: "",
            emotionArc: "",
            chapterHook: "",
            rawMarkdown: "raw",
          },
        ],
      },
    ],
    parseErrors: [],
  };
}

describe("ChapterTree", () => {
  test("renders volumes/chapters and shows details for active chapter", () => {
    const onSelectChapter = vi.fn();
    const outline = buildOutline();

    render(
      <ChapterTree
        outline={outline}
        currentChapter={{ volumeIndex: 0, chapterIndex: 0 }}
        completedChapters={new Set()}
        onSelectChapter={onSelectChapter}
      />,
    );

    expect(screen.getByRole("button", { name: /第一卷/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "第1章" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "第2章" })).toBeInTheDocument();

    expect(screen.getByText("事件：")).toBeInTheDocument();
    expect(screen.getByText("事件一")).toBeInTheDocument();
    expect(screen.getByText("情绪：")).toBeInTheDocument();
    expect(screen.getByText("情绪一")).toBeInTheDocument();
    expect(screen.getByText("钩子：")).toBeInTheDocument();
    expect(screen.getByText("钩子一")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "第2章" }));
    expect(onSelectChapter).toHaveBeenCalledWith(0, 1);
  });

  test("can collapse and expand a volume", () => {
    const outline = buildOutline();

    render(
      <ChapterTree
        outline={outline}
        currentChapter={null}
        completedChapters={new Set()}
        onSelectChapter={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /第一卷/ }));
    expect(screen.queryByRole("button", { name: "第1章" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "第2章" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /第一卷/ }));
    expect(screen.getByRole("button", { name: "第1章" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "第2章" })).toBeInTheDocument();
  });
});
