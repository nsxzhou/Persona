import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { ImportTxtDialog } from "@/components/import-txt-dialog";

const apiMock = vi.hoisted(() => ({
  previewNovelImport: vi.fn(),
  updateNovelImport: vi.fn(),
  commitNovelImport: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  api: apiMock,
}));

const pushMock = vi.hoisted(() => vi.fn());
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

function renderDialog() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <ImportTxtDialog
        open
        providers={[
          {
            id: "provider-1",
            label: "Provider",
            base_url: "https://api.example.test/v1",
            api_key_hint: "****1234",
            default_model: "gpt-4.1-mini",
            is_enabled: true,
            immersion_prompt_override_enabled: false,
            immersion_system_prompt_suffix: "",
            chat_test_system_prompt: "",
            last_test_status: null,
            last_test_error: null,
            last_tested_at: null,
            created_at: "2026-05-10T00:00:00Z",
            updated_at: "2026-05-10T00:00:00Z",
          },
        ]}
        styleProfiles={[]}
        plotProfiles={[]}
        onOpenChange={vi.fn()}
      />
    </QueryClientProvider>,
  );
}

describe("ImportTxtDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMock.previewNovelImport.mockResolvedValue({
      draft_id: "draft-1",
      project: {
        project_name: "导入项目",
        default_provider_id: "provider-1",
        default_model: "gpt-4.1-mini",
        style_profile_id: null,
        plot_profile_id: null,
        generation_profile: null,
      },
      chapters: [
        {
          client_id: "chapter-1",
          title: "第1章",
          content: "第一章正文",
          word_count: 5,
        },
      ],
      warnings: ["no_standard_chapter_headings"],
      created_at: "2026-05-10T00:00:00Z",
      expires_at: "2026-05-11T00:00:00Z",
    });
    apiMock.updateNovelImport.mockImplementation(async (_draftId, payload) => ({
      draft_id: "draft-1",
      ...payload,
      warnings: ["no_standard_chapter_headings"],
      created_at: "2026-05-10T00:00:00Z",
      expires_at: "2026-05-11T00:00:00Z",
    }));
    apiMock.commitNovelImport.mockResolvedValue({ project_id: "project-1" });
  });

  test("previews warnings, updates edited chapter, and commits", async () => {
    renderDialog();

    fireEvent.change(screen.getByLabelText("项目名称"), {
      target: { value: "导入项目" },
    });
    fireEvent.change(screen.getByLabelText("TXT 文件"), {
      target: {
        files: [new File(["正文"], "novel.txt", { type: "text/plain" })],
      },
    });
    fireEvent.click(screen.getByText("我确认拥有处理该 TXT 内容并创建改写项目的权利。"));
    fireEvent.click(screen.getByRole("button", { name: /解析预览/ }));

    await waitFor(() => {
      expect(apiMock.previewNovelImport).toHaveBeenCalledWith(
        expect.not.objectContaining({ length_preset: expect.anything() }),
      );
    });
    expect(screen.queryByText("篇幅预设")).not.toBeInTheDocument();
    expect(await screen.findByText("未识别标准章节标题，已作为单章导入")).toBeInTheDocument();
    const chapterBody = screen.getByLabelText("第 1 章正文");
    fireEvent.change(chapterBody, { target: { value: "改后正文" } });

    fireEvent.click(screen.getByRole("button", { name: "保存草稿" }));
    await waitFor(() => {
      expect(apiMock.updateNovelImport).toHaveBeenCalledWith(
        "draft-1",
        expect.objectContaining({
          chapters: [expect.objectContaining({ content: "改后正文" })],
        }),
      );
    });

    fireEvent.click(screen.getByRole("button", { name: "创建项目" }));
    await waitFor(() => {
      expect(apiMock.commitNovelImport).toHaveBeenCalledWith("draft-1");
      expect(pushMock).toHaveBeenCalledWith("/projects/project-1/editor");
    });
  });
});
