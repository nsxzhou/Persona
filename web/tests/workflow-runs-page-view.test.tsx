import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { WorkflowRunsPageView } from "@/components/workflow-runs-page-view";
import type { NovelWorkflowListItem, ProjectSummary } from "@/lib/types";

const apiMock = vi.hoisted(() => ({
  listNovelWorkflows: vi.fn(),
  getProjects: vi.fn(),
  clearNovelWorkflowHistory: vi.fn(),
}));

const toastMock = vi.hoisted(() => ({
  success: vi.fn(),
  error: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  api: apiMock,
}));

vi.mock("sonner", () => ({
  toast: toastMock,
}));

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>,
  );
}

const run: NovelWorkflowListItem = {
  id: "run-1",
  intent_type: "selection_rewrite",
  project_id: "project-1",
  chapter_id: "chapter-1",
  provider_id: "provider-1",
  project_name: "测试项目",
  chapter_title: "第一章",
  provider_label: "Primary",
  model_name: "gpt-test",
  status: "succeeded",
  stage: null,
  checkpoint_kind: null,
  latest_artifacts: [],
  warnings: [],
  error_message: null,
  started_at: "2026-05-07T01:00:00Z",
  completed_at: "2026-05-07T01:00:01Z",
  created_at: "2026-05-07T01:00:00Z",
  updated_at: "2026-05-07T01:00:01Z",
  pause_requested_at: null,
};

const project: ProjectSummary = {
  id: "project-1",
  name: "测试项目",
  description: "",
  status: "active",
  default_provider_id: "provider-1",
  default_model: "gpt-test",
  style_profile_id: null,
  plot_profile_id: null,
  generation_profile: null,
  length_preset: "short",
  archived_at: null,
  created_at: "2026-05-07T00:00:00Z",
  updated_at: "2026-05-07T00:00:00Z",
  provider: {
    id: "provider-1",
    label: "Primary",
    base_url: "https://api.example.test/v1",
    default_model: "gpt-test",
    is_enabled: true,
  },
};

describe("WorkflowRunsPageView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMock.listNovelWorkflows.mockResolvedValue([run]);
    apiMock.getProjects.mockResolvedValue([project]);
    apiMock.clearNovelWorkflowHistory.mockResolvedValue(undefined);
  });

  test("renders workflow runs and applies filters", async () => {
    renderWithClient(<WorkflowRunsPageView />);

    expect(await screen.findByText("局部改写")).toBeInTheDocument();
    expect(screen.getByText("测试项目")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /查看 Trace/ })).toHaveAttribute(
      "href",
      "/workflow-runs/run-1",
    );

    fireEvent.click(screen.getByLabelText("按状态过滤"));
    const successOptions = await screen.findAllByText("成功");
    fireEvent.click(successOptions[successOptions.length - 1]);

    await waitFor(() => {
      expect(apiMock.listNovelWorkflows).toHaveBeenLastCalledWith(
        expect.objectContaining({ status: "succeeded" }),
      );
    });
  });

  test("shows empty state", async () => {
    apiMock.listNovelWorkflows.mockResolvedValue([]);

    renderWithClient(<WorkflowRunsPageView />);

    expect(await screen.findByText("暂无运行记录。")).toBeInTheDocument();
    expect(within(screen.getByText("Workflow Runs").closest("div") ?? document.body).queryByText("局部改写")).not.toBeInTheDocument();
  });

  test("clears workflow run history after confirmation", async () => {
    renderWithClient(<WorkflowRunsPageView />);

    expect(await screen.findByText("局部改写")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "清空" }));
    fireEvent.click(screen.getByRole("button", { name: "清空" }));

    await waitFor(() => {
      expect(apiMock.clearNovelWorkflowHistory).toHaveBeenCalledTimes(1);
    });
    expect(toastMock.success).toHaveBeenCalledWith("运行历史已清空");
    await waitFor(() => {
      expect(apiMock.listNovelWorkflows).toHaveBeenCalledTimes(2);
    });
  });
});
