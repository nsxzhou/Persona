import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi } from "vitest";

import StyleLabPage from "@/app/(workspace)/style-lab/page";
import { StyleLabWizardView } from "@/components/style-lab-wizard-view";

const apiMock = vi.hoisted(() => ({
  getProviderConfigs: vi.fn(),
  getStyleAnalysisJobs: vi.fn(),
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
  return {
    executive_summary: {
      summary: "整体文风冷峻、短句密集、留白明显。",
      representative_evidence: [
        { excerpt: "夜色很冷。", location: "段落 1" },
        { excerpt: "他忽然笑了。", location: "段落 2" },
      ],
    },
    basic_assessment: {
      text_type: "章节正文",
      multi_speaker: false,
      batch_mode: false,
      location_indexing: "章节或段落位置",
      noise_handling: "未发现显著噪声。",
    },
    sections: [
      {
        section: "3.1",
        title: "口头禅与常用表达",
        overview: "高频短词集中出现。",
        findings: [
          {
            label: "冷感词",
            summary: "偏爱冷、笑、忽然等短词。",
            frequency: "高频",
            confidence: "high",
            is_weak_judgment: false,
            evidence: [{ excerpt: "夜色很冷。", location: "段落 1" }],
          },
        ],
      },
      {
        section: "3.2",
        title: "固定句式与节奏偏好",
        overview: "短句推进明显。",
        findings: [
          {
            label: "短句节奏",
            summary: "句间停顿明显。",
            frequency: "高频",
            confidence: "high",
            is_weak_judgment: false,
            evidence: [{ excerpt: "他忽然笑了。", location: "段落 2" }],
          },
        ],
      },
    ],
    appendix: "当前样本较短，附录省略详细索引。",
  };
}

function buildSummary(styleName = "旧名字") {
  return {
    style_name: styleName,
    style_positioning: "冷峻、克制、短句驱动。",
    core_features: ["短句推进", "留白明显"],
    lexical_preferences: ["冷", "笑", "忽然"],
    rhythm_profile: ["短句为主", "停顿明显"],
    punctuation_profile: ["句号收束多"],
    imagery_and_themes: ["夜色", "孤独"],
    scene_strategies: [
      { scene: "dialogue", instruction: "对白尽量短。" },
      { scene: "action", instruction: "动作描写利落。" },
    ],
    avoid_or_rare: ["避免抒情堆砌。"],
    generation_notes: ["优先保留冷感词和短句节奏。"],
  };
}

function buildPromptPack(systemPrompt = "以冷峻、克制的中文小说文风进行创作。") {
  return {
    system_prompt: systemPrompt,
    scene_prompts: {
      dialogue: "对白短促，保留言外之意。",
      action: "动作描写要利落。",
      environment: "环境描写服务情绪。",
    },
    hard_constraints: ["避免现代网络口吻。"],
    style_controls: {
      tone: "冷峻克制",
      rhythm: "短句驱动",
      evidence_anchor: "优先保留高置信特征",
    },
    few_shot_slots: [
      {
        label: "environment",
        type: "environment",
        text: "夜色像一把薄刀，贴着窗纸划过去。",
        purpose: "建立冷感氛围",
      },
    ],
  };
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

vi.mock("sonner", () => {
  return {
    toast: {
      success: vi.fn(),
      error: vi.fn(),
      loading: vi.fn(() => "toast-id"),
    },
  };
});

vi.mock("@/lib/api", () => {
  return {
    api: apiMock,
  };
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
  expect(apiMock.getStyleAnalysisJobStatus).toHaveBeenCalledWith("job-1");
  expect(apiMock.getStyleAnalysisJob).toHaveBeenCalledWith("job-1");
});

test("style lab wizard fetches mountable projects only when entering final step", async () => {
  apiMock.getStyleAnalysisJob.mockResolvedValue(
    buildSucceededJob({
      analysis_report: buildReport(),
      style_summary: buildSummary(),
      prompt_pack: buildPromptPack(),
      style_profile: null,
    }),
  );
  apiMock.getProjects.mockResolvedValue([]);

  renderWizard();

  expect(await screen.findByText("口头禅与常用表达")).toBeInTheDocument();
  expect(apiMock.getProjects).not.toHaveBeenCalled();

  fireEvent.click(screen.getByRole("button", { name: "审阅完毕，下一步" }));
  expect(apiMock.getProjects).not.toHaveBeenCalled();

  fireEvent.click(screen.getByRole("button", { name: "确认摘要，下一步" }));
  await waitFor(() => expect(apiMock.getProjects).toHaveBeenCalledTimes(1));
});

test("style lab wizard renders read-only report and saves new profile with mount", async () => {
  apiMock.getStyleAnalysisJob.mockResolvedValue(
    buildSucceededJob({
      analysis_report: buildReport(),
      style_summary: buildSummary(),
      prompt_pack: buildPromptPack(),
      style_profile: null,
    }),
  );
  apiMock.getProjects.mockResolvedValue([
    {
      id: "project-1",
      name: "风格挂载项目",
      description: "项目简介",
      status: "draft",
      default_model: "gpt-4.1-mini",
      style_profile_id: null,
      archived_at: null,
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
    analysis_report: buildReport(),
    style_summary: buildSummary("新名字"),
    prompt_pack: buildPromptPack("新的 system prompt"),
    created_at: "2026-04-09T00:02:00Z",
    updated_at: "2026-04-09T00:02:00Z",
  });

  renderWizard();

  expect(await screen.findByText("口头禅与常用表达")).toBeInTheDocument();
  
  fireEvent.click(screen.getByRole("button", { name: "审阅完毕，下一步" }));

  fireEvent.change(await screen.findByText("风格名称", { selector: "label" }).then(l => screen.getByLabelText("风格名称")), {
    target: { value: "新名字" },
  });
  
  fireEvent.click(screen.getByRole("button", { name: "确认摘要，下一步" }));

  fireEvent.change(await screen.findByText("System Prompt", { selector: "label" }).then(l => screen.getByLabelText("System Prompt")), {
    target: { value: "新的 system prompt" },
  });
  
  // Click mount select
  fireEvent.click(screen.getByRole("combobox"));
  fireEvent.click(await screen.findByRole("option", { name: "风格挂载项目" }));
  
  fireEvent.click(screen.getByRole("button", { name: "保存完成" }));

  await waitFor(() => expect(apiMock.createStyleProfile).toHaveBeenCalledTimes(1));
  await waitFor(() =>
    expect(apiMock.createStyleProfile).toHaveBeenCalledWith(
      expect.objectContaining({
        job_id: "job-1",
        mount_project_id: "project-1",
      }),
    ),
  );
  expect(apiMock.updateProject).not.toHaveBeenCalled();
  expect(apiMock.getStyleProfile).not.toHaveBeenCalled();
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
        analysis_report: buildReport(),
        style_summary: buildSummary("旧名字"),
        prompt_pack: buildPromptPack(),
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
    analysis_report: buildReport(),
    style_summary: buildSummary("覆盖后的名字"),
    prompt_pack: buildPromptPack("覆盖后的 system prompt"),
    created_at: "2026-04-09T00:02:00Z",
    updated_at: "2026-04-09T00:03:00Z",
  });

  renderWizard();

  fireEvent.click(await screen.findByRole("button", { name: "审阅完毕，下一步" }));

  fireEvent.change(screen.getByLabelText("风格名称"), {
    target: { value: "覆盖后的名字" },
  });
  
  fireEvent.click(screen.getByRole("button", { name: "确认摘要，下一步" }));

  fireEvent.click(await screen.findByRole("button", { name: "保存完成" }));

  await waitFor(() => expect(apiMock.updateStyleProfile).toHaveBeenCalledWith(
    "profile-1",
    expect.objectContaining({
      style_summary: expect.objectContaining({ style_name: "覆盖后的名字" }),
    }),
  ));
  expect(apiMock.getStyleProfile).not.toHaveBeenCalled();
});
