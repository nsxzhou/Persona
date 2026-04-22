import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, test, vi } from "vitest";

import PlotLabPage from "@/app/(workspace)/plot-lab/page";
import { PlotLabWizardView } from "@/components/plot-lab-wizard-view";

const apiMock = vi.hoisted(() => ({
  getProviderConfigs: vi.fn(),
  getPlotAnalysisJobs: vi.fn(),
  deletePlotAnalysisJob: vi.fn(),
  getPlotAnalysisJobStatus: vi.fn(),
  getPlotAnalysisJob: vi.fn(),
  getPlotAnalysisJobAnalysisReport: vi.fn(),
  getPlotAnalysisJobPlotSummary: vi.fn(),
  getPlotAnalysisJobPlotSkeleton: vi.fn(),
  getPlotAnalysisJobPromptPack: vi.fn(),
  getPlotAnalysisJobLogs: vi.fn(),
  createPlotAnalysisJob: vi.fn(),
  getPlotProfiles: vi.fn(),
  getPlotProfile: vi.fn(),
  createPlotProfile: vi.fn(),
  updatePlotProfile: vi.fn(),
  getProjects: vi.fn(),
}));

const mockPush = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

vi.mock("@/lib/api", () => ({
  api: apiMock,
}));

function buildReport() {
  return "# 执行摘要\n整体靠高压绑定、反截胡、修罗场失衡推进。\n";
}

function buildSummary(plotName = "旧名字") {
  return `# 剧情定位\n${plotName}\n\n# 读者追读抓手\n高压绑定 + 反派求生。\n`;
}

function buildSkeleton() {
  return "# 全书骨架\n## 阶段划分（按 chunk 索引）\n- 开局铺垫\n";
}

function buildPromptPack(systemPrompt = "保持高压绑定开局，不要洗白主角。") {
  return `# Shared Constraints\n${systemPrompt}\n`;
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

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

function renderDashboard(queryClient = createTestQueryClient()) {
  return render(
    <QueryClientProvider client={queryClient}>
      <PlotLabPage />
    </QueryClientProvider>,
  );
}

function renderWizard(queryClient = createTestQueryClient(), jobId = "job-1") {
  return render(
    <QueryClientProvider client={queryClient}>
      <PlotLabWizardView jobId={jobId} />
    </QueryClientProvider>,
  );
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
  apiMock.getPlotAnalysisJobAnalysisReport.mockResolvedValue(buildReport());
  apiMock.getPlotAnalysisJobPlotSummary.mockResolvedValue(buildSummary());
  apiMock.getPlotAnalysisJobPlotSkeleton.mockResolvedValue(buildSkeleton());
  apiMock.getPlotAnalysisJobPromptPack.mockResolvedValue(buildPromptPack());
  apiMock.getPlotAnalysisJobLogs.mockResolvedValue({
    content: "",
    next_offset: 0,
    truncated: false,
  });
});

test("plot lab page submits txt upload form", async () => {
  apiMock.getProviderConfigs.mockResolvedValueOnce([
    {
      id: "provider-1",
      label: "Primary Gateway",
      base_url: "https://api.openai.com/v1",
      default_model: "gpt-4.1-mini",
      api_key_hint: "****1234",
      is_enabled: true,
      last_test_status: null,
      last_test_error: null,
      last_tested_at: null,
      created_at: "2026-04-09T00:00:00Z",
      updated_at: "2026-04-09T00:00:00Z",
    },
  ]);
  apiMock.getPlotAnalysisJobs.mockResolvedValueOnce([]);
  apiMock.createPlotAnalysisJob.mockResolvedValueOnce({
    ...buildSucceededJob(),
    status: "pending",
    completed_at: null,
  });

  renderDashboard();

  fireEvent.click(await screen.findByRole("button", { name: "+ 新建分析任务" }));
  fireEvent.change(await screen.findByLabelText("情节档案名称"), {
    target: { value: "反派修罗场模板" },
  });
  fireEvent.change(screen.getByLabelText("TXT 样本"), {
    target: {
      files: [new File(["第一章 风雪夜归人"], "sample.txt", { type: "text/plain" })],
    },
  });
  fireEvent.click(screen.getByRole("button", { name: "开始分析" }));

  await waitFor(() => expect(apiMock.createPlotAnalysisJob).toHaveBeenCalledTimes(1));
  await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/plot-lab/job-1"));
});

test("plot lab wizard saves profile and mounts project", async () => {
  apiMock.getPlotAnalysisJob.mockResolvedValueOnce(buildSucceededJob());
  apiMock.getProjects.mockResolvedValueOnce([
    {
      id: "project-1",
      name: "情节挂载项目",
      description: "",
      status: "draft",
      default_provider_id: "provider-1",
      default_model: "gpt-4.1-mini",
      style_profile_id: null,
      plot_profile_id: null,
      length_preset: "short",
      archived_at: null,
      created_at: "2026-04-09T00:00:00Z",
      updated_at: "2026-04-09T00:00:00Z",
      provider: {
        id: "provider-1",
        label: "Primary Gateway",
        base_url: "https://api.openai.com/v1",
        default_model: "gpt-4.1-mini",
        is_enabled: true,
      },
    },
  ]);
  apiMock.createPlotProfile.mockResolvedValueOnce({
    id: "plot-profile-1",
  });

  renderWizard();

  fireEvent.click(await screen.findByRole("button", { name: "审阅完毕，下一步" }));
  fireEvent.click(await screen.findByRole("button", { name: "审阅完毕，下一步" }));
  fireEvent.click(await screen.findByRole("button", { name: "确认摘要，下一步" }));
  fireEvent.change(screen.getByLabelText("Prompt Pack Markdown"), {
    target: { value: "# Shared Constraints\n不要洗白主角\n" },
  });
  fireEvent.click(screen.getByRole("combobox"));
  fireEvent.click(await screen.findByText("情节挂载项目"));
  fireEvent.click(screen.getByRole("button", { name: "保存完成" }));

  await waitFor(() =>
    expect(apiMock.createPlotProfile).toHaveBeenCalledWith(
      expect.objectContaining({
        job_id: "job-1",
        plot_name: "已完成任务",
        plot_summary_markdown: buildSummary(),
        prompt_pack_markdown: "# Shared Constraints\n不要洗白主角\n",
        mount_project_id: "project-1",
      }),
    ),
  );
});

test("plot lab wizard log polling carries next offset forward", async () => {
  apiMock.getPlotAnalysisJobStatus.mockResolvedValue({
    id: "job-1",
    status: "running",
    stage: "analyzing_focus_chunks",
    error_message: null,
    updated_at: "2026-04-09T00:01:00Z",
  });
  apiMock.getPlotAnalysisJob.mockResolvedValue({
    ...buildSucceededJob({
      status: "running",
      completed_at: null,
      updated_at: "2026-04-09T00:00:30Z",
    }),
  });
  apiMock.getPlotAnalysisJobLogs
    .mockResolvedValueOnce({
      content: "[1] first chunk\n",
      next_offset: 16,
      truncated: false,
    })
    .mockResolvedValueOnce({
      content: "[2] second chunk\n",
      next_offset: 33,
      truncated: false,
    });

  renderWizard();

  await screen.findByText("正在分析中...");
  await waitFor(() => {
    expect(apiMock.getPlotAnalysisJobLogs).toHaveBeenNthCalledWith(1, "job-1", 0);
  });

  await waitFor(() => {
    expect(apiMock.getPlotAnalysisJobLogs).toHaveBeenNthCalledWith(2, "job-1", 16);
  }, { timeout: 4000 });
});

test("plot lab wizard keeps succeeded artifact queries stable across rerenders", async () => {
  apiMock.getPlotAnalysisJob.mockResolvedValue(buildSucceededJob());

  const queryClient = createTestQueryClient();
  const view = renderWizard(queryClient);

  await screen.findByText("完整分析报告");
  expect(apiMock.getPlotAnalysisJobAnalysisReport).toHaveBeenCalledTimes(1);
  expect(apiMock.getPlotAnalysisJobPlotSummary).toHaveBeenCalledTimes(1);
  expect(apiMock.getPlotAnalysisJobPlotSkeleton).toHaveBeenCalledTimes(1);
  expect(apiMock.getPlotAnalysisJobPromptPack).toHaveBeenCalledTimes(1);

  view.rerender(
    <QueryClientProvider client={queryClient}>
      <PlotLabWizardView jobId="job-1" />
    </QueryClientProvider>,
  );

  await screen.findByText("完整分析报告");
  expect(apiMock.getPlotAnalysisJobAnalysisReport).toHaveBeenCalledTimes(1);
  expect(apiMock.getPlotAnalysisJobPlotSummary).toHaveBeenCalledTimes(1);
  expect(apiMock.getPlotAnalysisJobPlotSkeleton).toHaveBeenCalledTimes(1);
  expect(apiMock.getPlotAnalysisJobPromptPack).toHaveBeenCalledTimes(1);
});
