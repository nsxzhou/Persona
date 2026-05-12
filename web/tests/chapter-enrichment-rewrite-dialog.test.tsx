import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, fireEvent, render, renderHook, screen } from "@testing-library/react";
import type { ComponentProps, ReactNode } from "react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { ChapterEnrichmentRewriteDialog } from "@/components/editor/chapter-enrichment-rewrite-dialog";
import {
  useChapterEnrichmentRewrite,
  type ChapterRewriteItem,
} from "@/hooks/use-chapter-enrichment-rewrite";
import type { ChapterRewriteBatch, ProjectChapter } from "@/lib/types";

const apiMock = vi.hoisted(() => ({
  getChapterRewriteBatches: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  api: apiMock,
}));

vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
    message: vi.fn(),
    success: vi.fn(),
  },
}));

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
    id: "item-1",
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

function buildBatch(chapter: ProjectChapter): ChapterRewriteBatch {
  return {
    id: "batch-1",
    user_id: "user-1",
    project_id: chapter.project_id,
    instruction: "增强情绪张力",
    expansion_ratio_percent: 20,
    status: "succeeded",
    stage: null,
    error_message: null,
    total_count: 1,
    generated_count: 1,
    failed_count: 0,
    applied_count: 0,
    current_item_id: null,
    current_chapter_id: null,
    current_chapter_title: null,
    started_at: "2026-05-10T00:00:00Z",
    completed_at: "2026-05-10T00:00:10Z",
    created_at: "2026-05-10T00:00:00Z",
    updated_at: "2026-05-10T00:00:10Z",
    items: [],
  };
}

function renderDialog(item = buildItem(), overrides: Partial<ComponentProps<typeof ChapterEnrichmentRewriteDialog>> = {}) {
  const onApplyOne = vi.fn();
  const onApplyAll = vi.fn();
  const onOpenChange = vi.fn();
  const onSelectChapter = vi.fn();
  const onSelectCurrentChapter = vi.fn();
  const onSelectAllChapters = vi.fn();
  const onClearSelectedChapters = vi.fn();
  const onActiveChapterChange = vi.fn();
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
      expansionRatioPercent={20}
      batch={null}
      isRunning={false}
      isApplying={false}
      onInstructionChange={vi.fn()}
      onExpansionRatioPercentChange={vi.fn()}
      onSelectChapter={onSelectChapter}
      onSelectCurrentChapter={onSelectCurrentChapter}
      onSelectAllChapters={onSelectAllChapters}
      onClearSelectedChapters={onClearSelectedChapters}
      onActiveChapterChange={onActiveChapterChange}
      onStart={vi.fn()}
      onApplyOne={onApplyOne}
      onApplyAll={onApplyAll}
      onOpenChange={onOpenChange}
      {...overrides}
    />,
  );

  return {
    onApplyOne,
    onApplyAll,
    onOpenChange,
    onSelectChapter,
    onSelectCurrentChapter,
    onSelectAllChapters,
    onClearSelectedChapters,
    onActiveChapterChange,
  };
}

describe("ChapterEnrichmentRewriteDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMock.getChapterRewriteBatches.mockResolvedValue([]);
  });

  test("fresh hook open focuses the current chapter without selecting chapters", () => {
    const firstChapter = buildChapter();
    const currentChapter = buildChapter({
      id: "chapter-2",
      chapter_index: 2,
      title: "第 2 章 试探江映娆",
    });
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(
      () =>
        useChapterEnrichmentRewrite({
          projectId: "project-1",
          chapters: [firstChapter, currentChapter],
          selectedChapter: currentChapter,
          onApplied: vi.fn(),
        }),
      { wrapper },
    );

    act(() => {
      result.current.openRewrite();
    });

    expect(result.current.isOpen).toBe(true);
    expect(result.current.activeChapterId).toBe(currentChapter.id);
    expect(result.current.selectedChapterIds.size).toBe(0);
    expect(result.current.instruction).toBe("");

    act(() => {
      result.current.selectCurrentChapter();
    });

    expect([...result.current.selectedChapterIds]).toEqual([currentChapter.id]);
    expect(result.current.activeChapterId).toBe(currentChapter.id);

    act(() => {
      result.current.setActiveChapterId(firstChapter.id);
      result.current.selectAllChapters();
    });

    expect(result.current.selectedChapterIds).toEqual(new Set([firstChapter.id, currentChapter.id]));
    expect(result.current.activeChapterId).toBe(firstChapter.id);

    act(() => {
      result.current.clearSelectedChapters();
    });

    expect(result.current.selectedChapterIds.size).toBe(0);
    expect(result.current.activeChapterId).toBe(firstChapter.id);

    act(() => {
      result.current.setInstruction("上一轮要求");
      result.current.closeRewrite();
    });

    act(() => {
      result.current.openRewrite();
    });

    expect(result.current.instruction).toBe("");
    expect(result.current.selectedChapterIds.size).toBe(0);
    expect(result.current.activeChapterId).toBe(currentChapter.id);
  });

  test("starts in a focused setup phase before any preview exists", () => {
    const item = buildItem({ state: "waiting", preview: "", statusLabel: "等待中" });
    renderDialog(item, {
      selectedChapterIds: new Set(),
      items: [],
      activeItem: null,
      activeChapterId: item.chapter.id,
    });

    expect(screen.getByLabelText("自由改写要求")).toBeInTheDocument();
    expect(screen.getByLabelText("扩写比例")).toHaveValue(20);
    expect(screen.getByText("选择章节")).toBeInTheDocument();
    expect(screen.getByText("已选 0 章 · 0 字")).toBeInTheDocument();
    expect(screen.getByText("尚未选择章节。点击复选框、选择当前章或全选后才能开始改写。")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "开始改写" })).toBeDisabled();
    expect(screen.queryByText("未选择")).toBeNull();
    expect(screen.getAllByText("未选").length).toBeGreaterThan(0);
    expect(screen.queryByText("当前正文")).toBeNull();
    expect(screen.queryByRole("button", { name: "应用当前" })).toBeNull();
  });

  test("setup selection controls call explicit selection handlers", () => {
    const item = buildItem({ state: "waiting", preview: "", statusLabel: "等待中" });
    const {
      onSelectCurrentChapter,
      onSelectAllChapters,
      onClearSelectedChapters,
    } = renderDialog(item, {
      selectedChapterIds: new Set([item.chapter.id]),
      items: [],
      activeItem: null,
      activeChapterId: item.chapter.id,
    });

    fireEvent.click(screen.getByRole("button", { name: "选择当前章" }));
    fireEvent.click(screen.getByRole("button", { name: "全选" }));
    fireEvent.click(screen.getByRole("button", { name: "清空" }));

    expect(onSelectCurrentChapter).toHaveBeenCalledTimes(1);
    expect(onSelectAllChapters).toHaveBeenCalledTimes(1);
    expect(onClearSelectedChapters).toHaveBeenCalledTimes(1);
  });

  test("chapter title changes focus without toggling selection", () => {
    const item = buildItem({ state: "waiting", preview: "", statusLabel: "等待中" });
    const { onActiveChapterChange, onSelectChapter } = renderDialog(item, {
      selectedChapterIds: new Set(),
      items: [],
      activeItem: null,
      activeChapterId: item.chapter.id,
    });

    fireEvent.click(screen.getByRole("button", { name: /第 2 章 试探江映娆/ }));

    expect(onActiveChapterChange).toHaveBeenCalledWith("chapter-2");
    expect(onSelectChapter).not.toHaveBeenCalled();

    fireEvent.click(screen.getByLabelText("选择 第 2 章 试探江映娆"));

    expect(onSelectChapter).toHaveBeenCalledWith("chapter-2", true);
  });

  test("exposes expansion ratio input with default value", () => {
    const onExpansionRatioPercentChange = vi.fn();
    renderDialog(buildItem({ state: "waiting", preview: "", statusLabel: "等待中" }), {
      onExpansionRatioPercentChange,
    });

    const input = screen.getByLabelText("扩写比例");
    expect(input).toHaveValue(20);
    fireEvent.change(input, { target: { value: "35" } });

    expect(onExpansionRatioPercentChange).toHaveBeenCalledWith(35);
  });

  test("renders a read-only side-by-side diff for the active chapter", () => {
    renderDialog();

    expect(screen.getByText("当前正文")).toBeInTheDocument();
    expect(screen.getByText("AI 暂存预览")).toBeInTheDocument();
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
    const { onApplyOne } = renderDialog(item, { batch: buildBatch(item.chapter) });

    fireEvent.click(screen.getByRole("button", { name: "应用当前" }));

    expect(onApplyOne).toHaveBeenCalledWith(item.chapter.id);
  });

  test("closing only hides the dialog without applying staged previews", () => {
    const item = buildItem();
    const { onApplyOne, onApplyAll, onOpenChange } = renderDialog(item, { batch: buildBatch(item.chapter) });

    fireEvent.click(screen.getByRole("button", { name: "关闭" }));

    expect(onOpenChange).toHaveBeenCalledWith(false);
    expect(onApplyOne).not.toHaveBeenCalled();
    expect(onApplyAll).not.toHaveBeenCalled();
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
    expect(screen.getByText("任务成功后在这里显示 AI 暂存预览。")).toBeInTheDocument();
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
