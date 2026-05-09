import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { PromptStackTab } from "@/components/prompt-stack-tab";
import { api } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  api: {
    getProjectPromptAssets: vi.fn(),
    previewProjectPromptStack: vi.fn(),
    createProjectPromptAsset: vi.fn(),
    updateProjectPromptAsset: vi.fn(),
    deleteProjectPromptAsset: vi.fn(),
    applyProjectPromptAssetSuggestions: vi.fn(),
    createNovelWorkflow: vi.fn(),
    waitForNovelWorkflow: vi.fn(),
    getNovelWorkflowArtifact: vi.fn(),
  },
}));

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>,
  );
}

const moonGateAsset = {
  id: "asset-1",
  project_id: "project-1",
  kind: "lorebook_entry" as const,
  scope: "project" as const,
  chapter_id: null,
  title: "Moon Gate",
  content: "Moon gate lore",
  keywords: ["moon"],
  enabled: true,
  always_on: false,
  priority: 3,
  created_at: "2026-05-09T00:00:00Z",
  updated_at: "2026-05-09T00:00:00Z",
};

const toneNoteAsset = {
  id: "asset-2",
  project_id: "project-1",
  kind: "author_note" as const,
  scope: "project" as const,
  chapter_id: null,
  title: "Tone Note",
  content: "Keep the prose tense.",
  keywords: [],
  enabled: true,
  always_on: true,
  priority: 1,
  created_at: "2026-05-09T00:00:00Z",
  updated_at: "2026-05-09T00:00:00Z",
};

describe("PromptStackTab", () => {
  test("shows state-adaptive empty onboarding when no assets exist", async () => {
    vi.mocked(api.getProjectPromptAssets).mockResolvedValue([]);

    renderWithQueryClient(<PromptStackTab projectId="project-1" chapters={[]} />);

    expect(await screen.findByText("还没有 Prompt 栈资产")).toBeInTheDocument();
    expect(screen.getByText(/基础小说资产会照常注入/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /生成初始化建议/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /手动新建资产/ })).toBeInTheDocument();
  });

  test("uses table management and collapsed diagnostics until preview is expanded", async () => {
    vi.mocked(api.getProjectPromptAssets).mockResolvedValue([moonGateAsset, toneNoteAsset]);
    vi.mocked(api.previewProjectPromptStack).mockResolvedValue({
      prompt: "# Active Lorebook Entries\n\n## Moon Gate\n\nMoon gate lore",
      manifest: {
        layers: [
          {
            key: "active_lorebook_entries",
            title: "Active Lorebook Entries",
            char_count: 56,
            assets: [
              {
                id: "asset-1",
                kind: "lorebook_entry",
                scope: "project",
                chapter_id: null,
                title: "Moon Gate",
                priority: 3,
                char_count: 14,
                match_reasons: ["keyword"],
                matched_keywords: ["moon"],
              },
            ],
          },
        ],
        selected_assets: [
          {
            id: "asset-1",
            kind: "lorebook_entry",
            scope: "project",
            chapter_id: null,
            title: "Moon Gate",
            priority: 3,
            char_count: 14,
            match_reasons: ["keyword"],
            matched_keywords: ["moon"],
          },
        ],
        total_selected_assets: 1,
        final_prompt_char_count: 56,
      },
    });

    renderWithQueryClient(<PromptStackTab projectId="project-1" chapters={[]} />);

    expect(await screen.findByText("资产管理")).toBeInTheDocument();
    expect(await screen.findByText("Moon Gate")).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "资产" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "触发方式" })).toBeInTheDocument();
    expect(screen.getByText("运行时预览诊断")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /预览注入结果/ })).not.toBeInTheDocument();

    fireEvent.click(screen.getByText("运行时预览诊断"));
    fireEvent.click(await screen.findByRole("button", { name: /预览注入结果/ }));

    await waitFor(() => {
      expect(api.previewProjectPromptStack).toHaveBeenCalledWith("project-1", {
        chapter_id: null,
        current_chapter_context: "",
        text_before_cursor: "",
        user_context: "",
      });
    });

    expect(await screen.findByText("最终 Prompt 栈片段")).toBeInTheDocument();
    expect(screen.getByText("1 项资产 · 56 字符")).toBeInTheDocument();
    expect(screen.getAllByText("#moon").length).toBeGreaterThan(0);

    const promptBlock = screen.getByText(/# Active Lorebook Entries/);
    expect(within(promptBlock).getByText(/Moon gate lore/)).toBeInTheDocument();
  });
});
