import { fireEvent, render, screen } from "@testing-library/react";
import type { ComponentProps } from "react";
import { describe, expect, test, vi } from "vitest";

import { ChapterEnrichmentRewriteDialog } from "@/components/editor/chapter-enrichment-rewrite-dialog";
import type { ChapterRewriteItem } from "@/hooks/use-chapter-enrichment-rewrite";
import type { ProjectChapter } from "@/lib/types";

function buildChapter(overrides: Partial<ProjectChapter> = {}): ProjectChapter {
  return {
    id: "chapter-1",
    project_id: "project-1",
    volume_index: 1,
    chapter_index: 1,
    title: "第 1 章 圣女阁下，你也不想……",
    content: "旧第一行\n保留行\n旧第三行",
    beats_markdown: "",
    summary: "",
    word_count: 12,
    created_at: "2026-05-10T00:00:00Z",
    updated_at: "2026-05-10T00:00:00Z",
    ...overrides,
  };
}

function buildItem(overrides: Partial<ChapterRewriteItem> = {}): ChapterRewriteItem {
  const chapter = buildChapter(overrides.chapter);
  return {
    chapter,
    state: "generated",
    jobId: "job-1",
    preview: "新第一行\n保留行\n新第三行",
    logs: "生成完成",
    statusLabel: "generated",
    errorMessage: null,
    applyErrorMessage: null,
    ...overrides,
  };
}

function renderDialog(item = buildItem(), overrides: Partial<ComponentProps<typeof ChapterEnrichmentRewriteDialog>> = {}) {
  const onApplyOne = vi.fn();
  const chapters = [item.chapter, buildChapter({ id: "chapter-2", chapter_index: 2, title: "第 2 章 试探江映娆" })];

  render(
    <ChapterEnrichmentRewriteDialog
      open
      chapters={chapters}
      selectedChapterIds={new Set([item.chapter.id])}
      items={[item]}
      activeItem={item}
      activeChapterId={item.chapter.id}
      instruction="增强情绪张力"
      isRunning={false}
      isApplying={false}
      onInstructionChange={vi.fn()}
      onSelectChapter={vi.fn()}
      onActiveChapterChange={vi.fn()}
      onStart={vi.fn()}
      onApplyOne={onApplyOne}
      onApplyAll={vi.fn()}
      onOpenChange={vi.fn()}
      {...overrides}
    />,
  );

  return { onApplyOne };
}

describe("ChapterEnrichmentRewriteDialog", () => {
  test("starts in a focused setup phase before any preview exists", () => {
    renderDialog(buildItem({ state: "waiting", preview: "", statusLabel: "等待中" }));

    expect(screen.getByLabelText("自由改写要求")).toBeInTheDocument();
    expect(screen.getByText("选择章节")).toBeInTheDocument();
    expect(screen.queryByText("未选择")).toBeNull();
    expect(screen.getByText("未选")).toBeInTheDocument();
    expect(screen.queryByText("当前正文")).toBeNull();
    expect(screen.queryByRole("button", { name: "应用当前" })).toBeNull();
  });

  test("renders a read-only side-by-side diff for the active chapter", () => {
    renderDialog();

    expect(screen.getByText("当前正文")).toBeInTheDocument();
    expect(screen.getByText("AI 改写预览")).toBeInTheDocument();
    expect(screen.getByText("旧第一行")).toBeInTheDocument();
    expect(screen.getByText("新第一行")).toBeInTheDocument();
    expect(screen.getByText("+2")).toBeInTheDocument();
    expect(screen.getByText("-2")).toBeInTheDocument();
    expect(screen.queryByRole("textbox", { name: /AI 改写预览/ })).toBeNull();
  });

  test("only changes mode hides unchanged lines", () => {
    renderDialog();

    expect(screen.getAllByText("保留行").length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("switch"));

    expect(screen.queryByText("保留行")).toBeNull();
    expect(screen.getByText("旧第一行")).toBeInTheDocument();
    expect(screen.getByText("新第一行")).toBeInTheDocument();
  });

  test("applies the active generated chapter", () => {
    const item = buildItem();
    const { onApplyOne } = renderDialog(item);

    fireEvent.click(screen.getByRole("button", { name: "应用当前" }));

    expect(onApplyOne).toHaveBeenCalledWith(item.chapter.id);
  });

  test("allows returning to setup after previews exist", () => {
    renderDialog();

    expect(screen.getByText("当前正文")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "返回配置" }));

    expect(screen.getByText("选择章节")).toBeInTheDocument();
    expect(screen.queryByText("当前正文")).toBeNull();
    expect(screen.getByRole("button", { name: "查看预览" })).toBeInTheDocument();
  });

  test("does not show deletion stats while preview is still empty", () => {
    const waitingItem = buildItem({ state: "waiting", preview: "", statusLabel: "等待中" });
    const generatedItem = buildItem({
      chapter: buildChapter({ id: "chapter-2", chapter_index: 2, title: "第 2 章 试探江映娆" }),
    });
    renderDialog(waitingItem, {
      items: [waitingItem, generatedItem],
    });

    expect(screen.getByText("+0")).toBeInTheDocument();
    expect(screen.getByText("-0")).toBeInTheDocument();
    expect(screen.getByText("任务成功后在这里显示 AI 改写正文。")).toBeInTheDocument();
  });

  test("keeps logs hidden by default and reveals failure details", () => {
    renderDialog(buildItem({ state: "generated", logs: "生成完成" }));
    expect(screen.queryByText("生成完成")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "查看日志" }));
    expect(screen.getByText("生成完成")).toBeInTheDocument();

    renderDialog(buildItem({ state: "failed", preview: "", errorMessage: "模型超时", statusLabel: "failed" }));
    expect(screen.getByText("模型超时")).toBeInTheDocument();
  });
});
