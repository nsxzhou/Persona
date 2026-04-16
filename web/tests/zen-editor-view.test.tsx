import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { ZenEditorView } from "@/components/zen-editor-view";
import type { Project } from "@/lib/types";

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

const completionMock = vi.hoisted(() => ({
  isGenerating: false,
  handleGenerate: vi.fn(),
  handleStop: vi.fn(),
}));

const beatGenerationMock = vi.hoisted(() => ({
  beats: [] as string[],
  setBeats: vi.fn(),
  currentBeatIndex: -1,
  isGeneratingBeats: false,
  isExpandingBeat: false,
  handleGenerateBeats: vi.fn(),
  handleStartBeatExpand: vi.fn(),
}));

const apiMock = vi.hoisted(() => ({
  getProjectChapters: vi.fn(),
  syncProjectChapters: vi.fn(),
  updateProjectChapter: vi.fn(),
  updateProject: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  api: {
    getProjectChapters: apiMock.getProjectChapters,
    syncProjectChapters: apiMock.syncProjectChapters,
    updateProjectChapter: apiMock.updateProjectChapter,
    updateProject: apiMock.updateProject,
  },
}));

vi.mock("@/hooks/use-editor-autosave", () => ({
  useEditorAutosave: () => ({ isSaving: false }),
}));

vi.mock("@/hooks/use-editor-completion", () => ({
  useEditorCompletion: () => completionMock,
}));

vi.mock("@/hooks/use-beat-generation", () => ({
  useBeatGeneration: () => beatGenerationMock,
}));

vi.mock("@/components/beat-panel", () => ({
  BeatPanel: ({ disabled }: { disabled?: boolean }) => (
    <button type="button" data-testid="beat-panel" disabled={disabled}>
      节拍面板
    </button>
  ),
}));

const navigationMock = vi.hoisted(() => ({
  push: vi.fn(),
}));

vi.mock("next/navigation", async () => {
  const actual = await vi.importActual<typeof import("next/navigation")>("next/navigation");
  return {
    ...actual,
    useRouter: () => navigationMock,
  };
});

const project: Project = {
  id: "project-1",
  name: "反派攻略手册",
  description: "",
  status: "active",
  default_provider_id: "provider-1",
  default_model: "gpt-4.1-mini",
  style_profile_id: "style-1",
  inspiration: "",
  world_building: "",
  characters: "",
  outline_master: "",
  outline_detail: `## 第一卷 反派开局
> 主打反转与误导

### 第1章 反派开局，短命名单
- **核心事件**：开局认命

### 第2章 纨绔是假装，天香楼才是入口
- **核心事件**：天香楼试探`,
  runtime_state: "",
  runtime_threads: "",
  length_preset: "short",
  archived_at: null,
  created_at: "2026-04-10T00:00:00Z",
  updated_at: "2026-04-10T00:00:00Z",
  provider: null as never,
};

const chapters = [
  {
    id: "chapter-1",
    project_id: "project-1",
    volume_index: 0,
    chapter_index: 0,
    title: "第1章 反派开局，短命名单",
    content: "第一章正文",
    word_count: 4,
    created_at: "2026-04-10T00:00:00Z",
    updated_at: "2026-04-10T00:00:00Z",
  },
  {
    id: "chapter-2",
    project_id: "project-1",
    volume_index: 0,
    chapter_index: 1,
    title: "第2章 纨绔是假装，天香楼才是入口",
    content: "",
    word_count: 0,
    created_at: "2026-04-10T00:00:00Z",
    updated_at: "2026-04-10T00:00:00Z",
  },
];

describe("ZenEditorView", () => {
  beforeEach(() => {
    completionMock.isGenerating = false;
    completionMock.handleGenerate.mockReset();
    completionMock.handleStop.mockReset();
    beatGenerationMock.beats = [];
    beatGenerationMock.setBeats.mockReset();
    beatGenerationMock.currentBeatIndex = -1;
    beatGenerationMock.isGeneratingBeats = false;
    beatGenerationMock.isExpandingBeat = false;
    beatGenerationMock.handleGenerateBeats.mockReset();
    beatGenerationMock.handleStartBeatExpand.mockReset();
    apiMock.getProjectChapters.mockReset();
    apiMock.syncProjectChapters.mockReset();
    apiMock.updateProjectChapter.mockReset();
    apiMock.updateProject.mockReset();
    apiMock.getProjectChapters.mockResolvedValue(chapters);
    apiMock.syncProjectChapters.mockResolvedValue(chapters);
    apiMock.updateProjectChapter.mockImplementation(async (_projectId, chapterId, payload) => ({
      ...chapters.find((chapter) => chapter.id === chapterId),
      content: payload.content,
      word_count: payload.content.length,
    }));
  });

  test("selects the first unwritten chapter by default", async () => {
    render(<ZenEditorView project={project} activeProfileName="娱乐春秋" />);

    await waitFor(() => {
      expect(screen.getAllByText("第2章 纨绔是假装，天香楼才是入口").length).toBeGreaterThan(0);
    });
    expect(screen.getByText("已定位章节")).toBeInTheDocument();
    expect(screen.getByRole("textbox")).toHaveValue("");
  });

  test("hydrates chapter selection from the editor entry context", async () => {
    render(
      <ZenEditorView
        project={project}
        activeProfileName="娱乐春秋"
        {...({
          initialChapterSelection: { volumeIndex: 0, chapterIndex: 1 },
          initialIntent: "generate_beats",
        } as Record<string, unknown>)}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText("当前章节")).toBeInTheDocument();
    });

    expect(screen.getAllByText("第2章 纨绔是假装，天香楼才是入口").length).toBeGreaterThan(0);
    expect(screen.getByText("已定位章节，准备生成节拍")).toBeInTheDocument();
    expect(screen.getByText("创作导航")).toBeInTheDocument();
    expect(screen.getByTestId("beat-panel")).toBeEnabled();
  });

  test("clicking another chapter swaps editor content instead of keeping previous chapter", async () => {
    render(<ZenEditorView project={project} activeProfileName="娱乐春秋" />);

    await waitFor(() => {
      expect(screen.getByRole("textbox")).toHaveValue("");
    });
    fireEvent.click(screen.getByTitle("创作导航 (⌘B)"));
    fireEvent.click(screen.getByRole("button", { name: /第1章 反派开局，短命名单/ }));

    await waitFor(() => {
      expect(screen.getByRole("textbox")).toHaveValue("第一章正文");
    });
    expect(screen.getByText("已定位章节")).toBeInTheDocument();
  });

  test("typing into the selected chapter does not get reset by chapter synchronization", async () => {
    render(<ZenEditorView project={project} activeProfileName="娱乐春秋" />);

    await waitFor(() => {
      expect(screen.getByRole("textbox")).toHaveValue("");
    });

    const textbox = screen.getByRole("textbox");
    fireEvent.change(textbox, { target: { value: "新写入的正文" } });

    await waitFor(() => {
      expect(screen.getByRole("textbox")).toHaveValue("新写入的正文");
    });
  });

  test("disables the editor textarea while streaming completion is active", async () => {
    completionMock.isGenerating = true;

    render(<ZenEditorView project={project} activeProfileName="娱乐春秋" />);

    await waitFor(() => {
      expect(screen.getByRole("textbox")).toBeDisabled();
    });
    expect(screen.getByRole("button", { name: /停止 \(Esc\)/ })).toBeInTheDocument();
  });

  test("disables the editor textarea while beat expansion is active", async () => {
    beatGenerationMock.isExpandingBeat = true;
    beatGenerationMock.beats = ["第一拍"];
    beatGenerationMock.currentBeatIndex = 0;

    render(<ZenEditorView project={project} activeProfileName="娱乐春秋" />);

    await waitFor(() => {
      expect(screen.getByRole("textbox")).toBeDisabled();
    });
  });

  test("book and settings rail buttons switch different left panel modes", async () => {
    render(<ZenEditorView project={project} activeProfileName="娱乐春秋" />);

    await waitFor(() => expect(screen.getByText("当前章节")).toBeInTheDocument());
    fireEvent.click(screen.getByTitle("创作设定"));

    expect(screen.getByText("运行时状态")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /第1章 反派开局，短命名单/ })).not.toBeInTheDocument();

    fireEvent.click(screen.getByTitle("创作导航 (⌘B)"));
    expect(screen.getByRole("button", { name: /第1章 反派开局，短命名单/ })).toBeInTheDocument();
  });

  test("allows collapsing the active volume while keeping current chapter banner", async () => {
    render(<ZenEditorView project={project} activeProfileName="娱乐春秋" />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /第2章 纨绔是假装/ })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /第一卷 反派开局/ }));

    expect(screen.queryByRole("button", { name: /第2章 纨绔是假装/ })).not.toBeInTheDocument();
    expect(screen.getByText("已定位章节")).toBeInTheDocument();
  });

  test("shows empty-state redirect when a volume has no chapter outline", async () => {
    render(
      <ZenEditorView
        project={{
          ...project,
          outline_detail: `## 第一幕：高危开局与关系占位
> 主题：先活下来，把必死反派改造成可操盘变量 | 字数范围：0-4万字

## 第二幕：洗白不是认怂，结盟就是换资源
> 主题：从单点自救转向结构经营，把名声、关系与组织力一起做出来 | 字数范围：4-8万字`,
        }}
        activeProfileName="娱乐春秋"
        {...({
          initialChapterSelection: { volumeIndex: 0, chapterIndex: 0 },
        } as Record<string, unknown>)}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText("当前分卷尚未生成章节细纲")).toBeInTheDocument();
    });

    expect(
      screen.getAllByText("请先回到「分卷与章节细纲」页为该分卷生成章节细纲").length,
    ).toBeGreaterThan(0);
    const goGenerateButtons = screen.getAllByRole("button", { name: "去生成本卷章节细纲" });
    expect(goGenerateButtons.length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "节拍写作" })).toBeDisabled();

    fireEvent.click(goGenerateButtons[0]);
    expect(navigationMock.push).toHaveBeenCalledWith("/projects/project-1?tab=outline_detail&volumeIndex=0");
  });
});
