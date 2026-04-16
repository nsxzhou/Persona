import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { ZenEditorView } from "@/components/zen-editor-view";

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock("@/lib/api", () => ({
  api: {
    updateProject: vi.fn(),
  },
}));

vi.mock("@/hooks/use-editor-autosave", () => ({
  useEditorAutosave: () => ({ isSaving: false }),
}));

vi.mock("@/hooks/use-editor-completion", () => ({
  useEditorCompletion: () => ({
    isGenerating: false,
    handleGenerate: vi.fn(),
    handleStop: vi.fn(),
  }),
}));

vi.mock("@/hooks/use-beat-generation", () => ({
  useBeatGeneration: () => ({
    beats: [],
    setBeats: vi.fn(),
    currentBeatIndex: -1,
    isGeneratingBeats: false,
    isExpandingBeat: false,
    handleGenerateBeats: vi.fn(),
    handleStartBeatExpand: vi.fn(),
  }),
}));

vi.mock("@/components/beat-panel", () => ({
  BeatPanel: () => <div data-testid="beat-panel">节拍面板</div>,
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

const project = {
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
  story_bible: "",
  content: "",
  length_preset: "short",
  archived_at: null,
  created_at: "2026-04-10T00:00:00Z",
  updated_at: "2026-04-10T00:00:00Z",
  provider: null,
};

describe("ZenEditorView", () => {
  test("shows empty current-chapter state before a chapter is selected", () => {
    render(<ZenEditorView project={project} activeProfileName="娱乐春秋" />);

    expect(screen.getByText("未选择章节")).toBeInTheDocument();
    expect(screen.getByText("请从右侧创作导航选择章节")).toBeInTheDocument();
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
    expect(screen.getByTestId("beat-panel")).toBeInTheDocument();
  });

  test("updates the current chapter banner after clicking a chapter in the side panel", async () => {
    render(<ZenEditorView project={project} activeProfileName="娱乐春秋" />);

    fireEvent.click(screen.getByTitle("创作导航 (Cmd+B)"));
    fireEvent.click(screen.getByRole("button", { name: /第1章 反派开局，短命名单/ }));

    await waitFor(() => {
      expect(screen.getAllByText("第1章 反派开局，短命名单").length).toBeGreaterThan(0);
    });
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
