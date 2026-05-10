import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { useBeatGeneration } from "@/hooks/use-beat-generation";
import type { Project, ProjectBible } from "@/lib/types";

const apiMock = vi.hoisted(() => ({
  runChapterExpandWorkflow: vi.fn(),
}));

const toastMock = vi.hoisted(() => ({
  error: vi.fn(),
  message: vi.fn(),
}));

const editorState = vi.hoisted(() => ({
  content: "",
  setContent: vi.fn((next: string) => {
    editorState.content = next;
  }),
}));

vi.mock("@/lib/api", () => ({
  api: apiMock,
}));

vi.mock("sonner", () => ({
  toast: toastMock,
}));

vi.mock("@/components/editor/editor-context", () => ({
  useEditorContext: () => ({
    store: {
      getState: () => editorState,
    },
  }),
}));

vi.mock("@/hooks/use-streaming-text", () => ({
  useStreamingText: () => ({
    consumeResponse: vi.fn(async ({ onFlush }: { onFlush: (fullText: string) => void }) => {
      onFlush("完整章节正文");
      return "完整章节正文";
    }),
  }),
}));

const project = {
  id: "project-1",
  name: "反派攻略手册",
  style_profile_id: "style-1",
  plot_profile_id: "plot-1",
} as Project;

const projectBible = {
  runtime_state: "运行状态",
  runtime_threads: "伏笔",
  outline_detail: "章节细纲",
} as ProjectBible;

function responseFromText(text: string): Response {
  return new Response(`data: ${JSON.stringify(text)}\n\n`);
}

describe("useBeatGeneration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    editorState.content = "";
    window.confirm = vi.fn(() => true);
    apiMock.runChapterExpandWorkflow.mockResolvedValue({
      response: responseFromText("完整章节正文"),
      reviewIssues: [],
    });
  });

  test("expands all beats with one full-chapter workflow call", async () => {
    const onBeatExpandCompleted = vi.fn();
    const { result } = renderHook(() =>
      useBeatGeneration({
        project,
        projectBible,
        textareaRef: { current: null },
        isGenerating: false,
        chapterId: "chapter-1",
        currentChapterContext: "当前章节",
        previousChapterContext: "前章摘要",
        onBeatExpandCompleted,
      }),
    );

    act(() => {
      result.current.setBeats([
        "第一拍",
        "第二拍",
        "第三拍",
        "第四拍",
        "第五拍",
        "第六拍",
        "第七拍",
        "第八拍",
      ]);
    });
    await act(async () => {
      await result.current.handleStartBeatExpand();
    });

    expect(apiMock.runChapterExpandWorkflow).toHaveBeenCalledTimes(1);
    expect(apiMock.runChapterExpandWorkflow).toHaveBeenCalledWith(
      "project-1",
      "chapter-1",
      "",
      "运行状态",
      "伏笔",
      "章节细纲",
      ["第一拍", "第二拍", "第三拍", "第四拍", "第五拍", "第六拍", "第七拍", "第八拍"],
      "当前章节",
      "前章摘要",
      "style-1",
      "plot-1",
      undefined,
    );
    expect(editorState.setContent).toHaveBeenCalledWith("完整章节正文");
    expect(onBeatExpandCompleted).toHaveBeenCalledWith("完整章节正文");
  });

  test("asks before replacing non-empty chapter content and leaves content unchanged on cancel", async () => {
    editorState.content = "已有正文";
    window.confirm = vi.fn(() => false);
    const { result } = renderHook(() =>
      useBeatGeneration({
        project,
        projectBible,
        textareaRef: { current: null },
        isGenerating: false,
      }),
    );

    act(() => {
      result.current.setBeats(["第一拍"]);
    });
    await act(async () => {
      await result.current.handleStartBeatExpand();
    });

    expect(window.confirm).toHaveBeenCalled();
    expect(apiMock.runChapterExpandWorkflow).not.toHaveBeenCalled();
    expect(editorState.content).toBe("已有正文");
  });

  test("passes regeneration output and feedback and shows review issues after delivery", async () => {
    editorState.content = "旧正文";
    apiMock.runChapterExpandWorkflow.mockResolvedValue({
      response: responseFromText("完整章节正文"),
      reviewIssues: ["漏掉第 3 拍", "章末钩子偏弱"],
    });
    const { result } = renderHook(() =>
      useBeatGeneration({
        project,
        projectBible,
        textareaRef: { current: null },
        isGenerating: false,
      }),
    );

    act(() => {
      result.current.setBeats(["第一拍", "第二拍"]);
    });
    await act(async () => {
      await result.current.handleStartBeatExpand({
        previousOutput: "旧正文",
        userFeedback: "强化结尾",
      });
    });

    expect(window.confirm).not.toHaveBeenCalled();
    expect(apiMock.runChapterExpandWorkflow).toHaveBeenCalledWith(
      expect.any(String),
      null,
      "",
      expect.any(String),
      expect.any(String),
      expect.any(String),
      ["第一拍", "第二拍"],
      undefined,
      "",
      "style-1",
      "plot-1",
      {
        previousOutput: "旧正文",
        userFeedback: "强化结尾",
      },
    );
    expect(editorState.setContent).toHaveBeenCalledWith("完整章节正文");
    expect(toastMock.message).toHaveBeenCalledWith("章节审校提示：漏掉第 3 拍；章末钩子偏弱");
  });
});
