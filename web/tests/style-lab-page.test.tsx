import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, vi } from "vitest";

import StyleLabPage from "@/app/(workspace)/style-lab/page";
import { StyleLabWizardView } from "@/components/style-lab-wizard-view";

const apiMock = vi.hoisted(() => ({
  getProviderConfigs: vi.fn(),
  getStyleAnalysisJobs: vi.fn(),
  deleteStyleAnalysisJob: vi.fn(),
  getStyleAnalysisJobStatus: vi.fn(),
  getStyleAnalysisJob: vi.fn(),
  createStyleAnalysisJob: vi.fn(),
  getStyleProfiles: vi.fn(),
  getStyleProfile: vi.fn(),
  createStyleProfile: vi.fn(),
  updateStyleProfile: vi.fn(),
  getProjects: vi.fn(),
  updateProject: vi.fn(),
}));

function buildReport() {
  return "# 执行摘要\n整体文风冷峻、短句密集、留白明显。\n\n## 3.1 口头禅与常用表达\n夜色很冷。\n";
}

function buildSummary(styleName = "旧名字") {
  return `# 风格名称\n${styleName}\n\n# 风格定位\n冷峻、克制、短句驱动。\n`;
}

function buildPromptPack(systemPrompt = "以冷峻、克制的中文小说文风进行创作。") {
  return `# System Prompt\n${systemPrompt}\n`;
}

function buildSucceededJob(overrides?: Record<string, unknown>) {
  return {
    id: "job-1",
    style_name: "已完成任务",
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
    style_profile_id: null,
    ...overrides,
  };
}

const mockPush = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    loading: vi.fn(() => "toast-id"),
  },
}));

vi.mock("@/lib/api", () => ({
  api: apiMock,
}));

beforeEach(() => {
  vi.resetAllMocks();
  apiMock.getStyleAnalysisJobStatus.mockResolvedValue({
    id: "job-1",
    status: "succeeded",
    stage: null,
    error_message: null,
    updated_at: "2026-04-09T00:01:00Z",
  });
});

function renderDashboard() {
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <StyleLabPage />
    </QueryClientProvider>,
  );
}

function renderWizard() {
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <StyleLabWizardView jobId="job-1" />
    </QueryClientProvider>,
  );
}

test("style lab page submits txt upload form", async () => {
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
  apiMock.getStyleAnalysisJobs.mockResolvedValueOnce([]);
  apiMock.createStyleAnalysisJob.mockResolvedValueOnce({
    ...buildSucceededJob(),
    status: "pending",
    completed_at: null,
  });

  renderDashboard();

  fireEvent.click(await screen.findByRole("button", { name: "+ 新建分析任务" }));
  fireEvent.change(await screen.findByLabelText("风格档案名称"), {
    target: { value: "金庸武侠风" },
  });
  fireEvent.change(screen.getByLabelText("TXT 样本"), {
    target: {
      files: [new File(["第一章 风雪夜归人"], "sample.txt", { type: "text/plain" })],
    },
  });
  fireEvent.click(screen.getByRole("button", { name: "开始分析" }));

  await waitFor(() => expect(apiMock.createStyleAnalysisJob).toHaveBeenCalledTimes(1));
  await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/style-lab/job-1"));
});

test("style lab page opens delete confirm dialog when clicking delete", async () => {
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
  apiMock.getStyleAnalysisJobs.mockResolvedValueOnce([
    buildSucceededJob({
      id: "job-delete",
      style_name: "可删除任务",
    }),
  ]);
  apiMock.deleteStyleAnalysisJob.mockResolvedValueOnce(undefined);

  renderDashboard();

  await screen.findByText("可删除任务");
  fireEvent.click(screen.getByTitle("删除任务"));

  expect(await screen.findByText("确定要删除该分析任务吗？")).toBeInTheDocument();
});

test("style lab wizard shows running stage feedback", async () => {
  apiMock.getStyleAnalysisJobStatus.mockResolvedValueOnce({
    id: "job-1",
    status: "running",
    stage: "preparing_input",
    error_message: null,
    updated_at: "2026-04-09T00:00:30Z",
  });
  apiMock.getStyleAnalysisJob.mockResolvedValueOnce({
    ...buildSucceededJob(),
    status: "running",
    stage: "preparing_input",
  });
  apiMock.getProjects.mockResolvedValueOnce([]);

  renderWizard();

  expect(await screen.findByText("当前阶段: preparing_input")).toBeInTheDocument();
});

test("style lab wizard shows backend failure message on terminal failed status", async () => {
  apiMock.getStyleAnalysisJobStatus.mockResolvedValueOnce({
    id: "job-1",
    status: "failed",
    stage: null,
    error_message: "报告生成失败：缺少有效 evidence",
    updated_at: "2026-04-09T00:01:00Z",
  });
  apiMock.getStyleAnalysisJob.mockResolvedValueOnce(
    buildSucceededJob({
      status: "failed",
      stage: null,
      error_message: "报告生成失败：缺少有效 evidence",
      completed_at: "2026-04-09T00:01:00Z",
    }),
  );
  apiMock.getProjects.mockResolvedValueOnce([]);

  renderWizard();

  expect(await screen.findByText("分析失败: 报告生成失败：缺少有效 evidence")).toBeInTheDocument();
});

test("style lab wizard fetches mountable projects only when entering final step", async () => {
  apiMock.getStyleAnalysisJob.mockResolvedValue(
    buildSucceededJob({
      analysis_report_markdown: buildReport(),
      style_summary_markdown: buildSummary(),
      prompt_pack_markdown: buildPromptPack(),
      style_profile: null,
    }),
  );
  apiMock.getProjects.mockResolvedValue([]);

  renderWizard();

  expect(await screen.findByText(/执行摘要/)).toBeInTheDocument();
  expect(apiMock.getProjects).not.toHaveBeenCalled();

  fireEvent.click(screen.getByRole("button", { name: "审阅完毕，下一步" }));
  expect(apiMock.getProjects).not.toHaveBeenCalled();

  fireEvent.click(screen.getByRole("button", { name: "确认摘要，下一步" }));
  await waitFor(() => expect(apiMock.getProjects).toHaveBeenCalledTimes(1));
});

test("style lab wizard renders markdown report and saves new profile with mount", async () => {
  apiMock.getStyleAnalysisJob.mockResolvedValue(
    buildSucceededJob({
      analysis_report_markdown: buildReport(),
      style_summary_markdown: buildSummary(),
      prompt_pack_markdown: buildPromptPack(),
      style_profile: null,
    }),
  );
  apiMock.getProjects.mockResolvedValue([
    {
      id: "project-1",
      name: "风格挂载项目",
      description: "项目简介",
      status: "draft",
      default_provider_id: "provider-1",
      default_model: "gpt-4.1-mini",
      style_profile_id: null,
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
  apiMock.createStyleProfile.mockResolvedValueOnce({
    id: "profile-1",
    source_job_id: "job-1",
    provider_id: "provider-1",
    model_name: "gpt-4.1-mini",
    source_filename: "sample.txt",
    style_name: "新名字",
    analysis_report_markdown: buildReport(),
    style_summary_markdown: buildSummary("新名字"),
    prompt_pack_markdown: buildPromptPack("新的 system prompt"),
    created_at: "2026-04-09T00:02:00Z",
    updated_at: "2026-04-09T00:02:00Z",
  });

  renderWizard();

  expect(await screen.findByText(/执行摘要/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "审阅完毕，下一步" }));
  fireEvent.change(screen.getByLabelText("风格名称"), {
    target: { value: "新名字" },
  });
  fireEvent.change(screen.getByLabelText("风格摘要 Markdown"), {
    target: { value: "# 风格名称\n新名字\n" },
  });

  fireEvent.click(screen.getByRole("button", { name: "确认摘要，下一步" }));
  await waitFor(() => expect(apiMock.getProjects).toHaveBeenCalledTimes(1));

  fireEvent.change(screen.getByLabelText("Prompt Pack Markdown"), {
    target: { value: "# System Prompt\n新的 system prompt\n" },
  });
  fireEvent.click(screen.getByRole("combobox"));
  fireEvent.click(await screen.findByText("风格挂载项目"));
  fireEvent.click(screen.getByRole("button", { name: "保存完成" }));

  await waitFor(() =>
    expect(apiMock.createStyleProfile).toHaveBeenCalledWith(
      expect.objectContaining({
        job_id: "job-1",
        style_name: "新名字",
        style_summary_markdown: "# 风格名称\n新名字\n",
        prompt_pack_markdown: "# System Prompt\n新的 system prompt\n",
        mount_project_id: "project-1",
      }),
    ),
  );
});

test("style lab wizard updates existing saved profile", async () => {
  apiMock.getStyleAnalysisJob.mockResolvedValue(
    buildSucceededJob({
      style_profile_id: "profile-1",
      style_profile: {
        id: "profile-1",
        source_job_id: "job-1",
        provider_id: "provider-1",
        model_name: "gpt-4.1-mini",
        source_filename: "sample.txt",
        style_name: "旧名字",
        analysis_report_markdown: buildReport(),
        style_summary_markdown: buildSummary("旧名字"),
        prompt_pack_markdown: buildPromptPack(),
        created_at: "2026-04-09T00:02:00Z",
        updated_at: "2026-04-09T00:02:00Z",
      },
    }),
  );
  apiMock.getProjects.mockResolvedValue([]);
  apiMock.updateStyleProfile.mockResolvedValueOnce({
    id: "profile-1",
    source_job_id: "job-1",
    provider_id: "provider-1",
    model_name: "gpt-4.1-mini",
    source_filename: "sample.txt",
    style_name: "覆盖后的名字",
    analysis_report_markdown: buildReport(),
    style_summary_markdown: buildSummary("覆盖后的名字"),
    prompt_pack_markdown: buildPromptPack("覆盖后的 system prompt"),
    created_at: "2026-04-09T00:02:00Z",
    updated_at: "2026-04-09T00:03:00Z",
  });

  renderWizard();

  fireEvent.click(await screen.findByRole("button", { name: "审阅完毕，下一步" }));
  fireEvent.change(screen.getByLabelText("风格名称"), {
    target: { value: "覆盖后的名字" },
  });
  fireEvent.change(screen.getByLabelText("风格摘要 Markdown"), {
    target: { value: "# 风格名称\n覆盖后的名字\n" },
  });
  fireEvent.click(screen.getByRole("button", { name: "确认摘要，下一步" }));
  fireEvent.change(screen.getByLabelText("Prompt Pack Markdown"), {
    target: { value: "# System Prompt\n覆盖后的 system prompt\n" },
  });
  fireEvent.click(screen.getByRole("button", { name: "保存完成" }));

  await waitFor(() =>
    expect(apiMock.updateStyleProfile).toHaveBeenCalledWith(
      "profile-1",
      expect.objectContaining({
        style_name: "覆盖后的名字",
        style_summary_markdown: "# 风格名称\n覆盖后的名字\n",
      }),
    ),
  );
});
