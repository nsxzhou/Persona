import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, test, vi } from "vitest";

import { PlotLabWizardView } from "@/components/plot-lab-wizard-view";

const apiMock = vi.hoisted(() => ({
  getPlotAnalysisJobStatus: vi.fn(),
  getPlotAnalysisJob: vi.fn(),
  getPlotAnalysisJobAnalysisReport: vi.fn(),
  getPlotAnalysisJobPlotSkeleton: vi.fn(),
  getPlotAnalysisJobStoryEngine: vi.fn(),
  getPlotAnalysisJobLogs: vi.fn(),
  getPlotProfile: vi.fn(),
  createPlotProfile: vi.fn(),
  updatePlotProfile: vi.fn(),
  resumePlotAnalysisJob: vi.fn(),
  pausePlotAnalysisJob: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/lib/api", () => ({
  api: apiMock,
}));

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

function renderWizard(queryClient = createTestQueryClient(), jobId = "job-1") {
  return render(
    <QueryClientProvider client={queryClient}>
      <PlotLabWizardView jobId={jobId} />
    </QueryClientProvider>,
  );
}

function buildReport() {
  return "# 执行摘要\n整体靠高压绑定、反截胡、修罗场失衡推进。\n";
}

function buildSkeleton() {
  return "# 全书骨架\n## 阶段划分（按 chunk 索引）\n- 开局铺垫\n";
}

function buildStoryEngine() {
  return "# Plot Writing Guide\n## Core Plot Formula\n- 用压力迫使主角行动。\n";
}

function buildPlotWritingGuidePayload() {
  return {
    core_plot_formula: ["用压力迫使主角行动。"],
    chapter_progression_loop: ["目标 -> 阻碍 -> 行动 -> 小兑现 -> 新压力。"],
    scene_construction_rules: ["每个场景必须改变局面。"],
    setup_and_payoff_rules: ["伏笔必须参与行动兑现。"],
    payoff_and_tension_rhythm: ["半兑现后追加更大压力。"],
    side_plot_usage: ["支线必须回流主线。"],
    hook_recipes: ["胜利后揭示代价。"],
    anti_drift_rules: ["不要复述样本剧情。"],
  };
}

function buildSucceededJob(overrides?: Record<string, unknown>) {
  return {
    id: "job-1",
    plot_name: "已完成任务",
    provider_id: "provider-1",
    model_name: "gpt-4.1-mini",
    status: "succeeded",
    stage: null,
    error_message: null,
    started_at: "2026-04-09T00:00:00Z",
    completed_at: "2026-04-09T00:01:00Z",
    created_at: "2026-04-09T00:00:00Z",
    updated_at: "2026-04-09T00:01:00Z",
    provider: {
      id: "provider-1",
      label: "Primary Gateway",
      base_url: "https://api.openai.com/v1",
      default_model: "gpt-4.1-mini",
      is_enabled: true,
    },
    sample_file: {
      id: "sample-1",
      original_filename: "sample.txt",
      content_type: "text/plain",
      byte_size: 12,
      character_count: 12,
      checksum_sha256: "abc",
      created_at: "2026-04-09T00:00:00Z",
      updated_at: "2026-04-09T00:01:00Z",
    },
    plot_profile_id: null,
    ...overrides,
  };
}

beforeEach(() => {
  vi.resetAllMocks();
  apiMock.getPlotAnalysisJobStatus.mockResolvedValue({
    id: "job-1",
    status: "succeeded",
    stage: null,
    error_message: null,
    updated_at: "2026-04-09T00:01:00Z",
  });
  apiMock.getPlotAnalysisJob.mockResolvedValue(buildSucceededJob());
  apiMock.getPlotAnalysisJobAnalysisReport.mockResolvedValue(buildReport());
  apiMock.getPlotAnalysisJobPlotSkeleton.mockResolvedValue(buildSkeleton());
  apiMock.getPlotAnalysisJobStoryEngine.mockResolvedValue(buildStoryEngine());
  apiMock.getPlotAnalysisJobLogs.mockResolvedValue({
    content: "",
    next_offset: 0,
    truncated: false,
  });
});

test("plot lab wizard saves profile", async () => {
  apiMock.createPlotProfile.mockResolvedValueOnce({
    id: "plot-profile-1",
    source_job_id: "job-1",
    provider_id: "provider-1",
    model_name: "gpt-4.1-mini",
    source_filename: "sample.txt",
    plot_name: "已完成任务",
    analysis_report_markdown: buildReport(),
    story_engine_payload: buildPlotWritingGuidePayload(),
    story_engine_markdown: buildStoryEngine(),
    plot_skeleton_markdown: "# 全书骨架\n- 新骨架\n",
    created_at: "2026-04-09T00:02:00Z",
    updated_at: "2026-04-09T00:02:00Z",
  });

  renderWizard();

  fireEvent.click(await screen.findByRole("button", { name: "审阅完毕，下一步" }));
  fireEvent.change(screen.getByLabelText("全书骨架 Markdown"), {
    target: { value: "# 全书骨架\n- 新骨架\n" },
  });
  fireEvent.click(await screen.findByRole("button", { name: "审阅完毕，下一步" }));
  fireEvent.change(await screen.findByLabelText("Story Engine Markdown"), {
    target: { value: "# Plot Writing Guide\n## Core Plot Formula\n- 用压力迫使主角行动。\n" },
  });
  fireEvent.click(screen.getByRole("button", { name: "确认 Story Engine" }));

  await waitFor(() =>
    expect(apiMock.createPlotProfile).toHaveBeenCalledWith(
      expect.objectContaining({
        job_id: "job-1",
        plot_name: "已完成任务",
        plot_skeleton_markdown: "# 全书骨架\n- 新骨架\n",
        story_engine_markdown: "# Plot Writing Guide\n## Core Plot Formula\n- 用压力迫使主角行动。\n",
      }),
    ),
  );
});

test("plot lab profile view shows and updates skeleton markdown", async () => {
  apiMock.getPlotAnalysisJob.mockResolvedValueOnce(
    buildSucceededJob({
      plot_profile_id: "plot-profile-1",
    }),
  );
  apiMock.getPlotProfile.mockResolvedValueOnce({
    id: "plot-profile-1",
    source_job_id: "job-1",
    provider_id: "provider-1",
    model_name: "gpt-4.1-mini",
    source_filename: "sample.txt",
    plot_name: "已保存情节档案",
    analysis_report_markdown: buildReport(),
    story_engine_payload: buildPlotWritingGuidePayload(),
    story_engine_markdown: buildStoryEngine(),
    plot_skeleton_markdown: "# 全书骨架\n- 已保存骨架\n",
    created_at: "2026-04-09T00:00:00Z",
    updated_at: "2026-04-09T00:01:00Z",
  });
  apiMock.updatePlotProfile.mockResolvedValueOnce({
    id: "plot-profile-1",
  });

  renderWizard();

  expect(await screen.findByText("已保存情节档案")).toBeInTheDocument();
  const skeletonTab = screen.getByRole("tab", { name: "全书骨架" });
  fireEvent.click(screen.getByRole("button", { name: "编辑档案" }));
  fireEvent.mouseDown(skeletonTab);
  fireEvent.click(skeletonTab);
  fireEvent.change(screen.getByLabelText("全书骨架 Markdown"), {
    target: { value: "# 全书骨架\n- 更新后的骨架\n" },
  });
  fireEvent.click(screen.getAllByRole("button", { name: "保存修改" })[0]);

  await waitFor(() =>
    expect(apiMock.updatePlotProfile).toHaveBeenCalledWith(
      "plot-profile-1",
      expect.objectContaining({
        plot_name: "已保存情节档案",
        plot_skeleton_markdown: "# 全书骨架\n- 更新后的骨架\n",
      }),
    ),
  );
});

test("plot lab wizard keeps succeeded artifact queries stable across rerenders", async () => {
  const queryClient = createTestQueryClient();
  const view = renderWizard(queryClient);

  await screen.findByText(/执行摘要/);
  expect(apiMock.getPlotAnalysisJobAnalysisReport).toHaveBeenCalledTimes(1);
  expect(apiMock.getPlotAnalysisJobPlotSkeleton).toHaveBeenCalledTimes(1);
  expect(apiMock.getPlotAnalysisJobStoryEngine).toHaveBeenCalledTimes(1);

  view.rerender(
    <QueryClientProvider client={queryClient}>
      <PlotLabWizardView jobId="job-1" />
    </QueryClientProvider>,
  );

  await screen.findByText(/执行摘要/);
  expect(apiMock.getPlotAnalysisJobAnalysisReport).toHaveBeenCalledTimes(1);
  expect(apiMock.getPlotAnalysisJobPlotSkeleton).toHaveBeenCalledTimes(1);
  expect(apiMock.getPlotAnalysisJobStoryEngine).toHaveBeenCalledTimes(1);
});
