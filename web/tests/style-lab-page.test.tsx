import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi } from "vitest";

import StyleLabPage from "@/app/(workspace)/style-lab/page";

const apiMock = vi.hoisted(() => ({
  getProviderConfigs: vi.fn(),
  getStyleAnalysisJobs: vi.fn(),
  getStyleAnalysisJob: vi.fn(),
  createStyleAnalysisJob: vi.fn(),
  getStyleProfiles: vi.fn(),
  createStyleProfile: vi.fn(),
  getProjects: vi.fn(),
  updateProject: vi.fn(),
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

function renderPage() {
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <StyleLabPage />
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
  apiMock.getStyleProfiles.mockResolvedValueOnce([]);
  apiMock.getProjects.mockResolvedValueOnce([]);
  apiMock.createStyleAnalysisJob.mockResolvedValueOnce({
    id: "job-1",
    style_name: "金庸武侠风",
    provider_id: "provider-1",
    model_name: "gpt-4.1-mini",
    status: "pending",
    stage: null,
    error_message: null,
    started_at: null,
    completed_at: null,
    created_at: "2026-04-09T00:00:00Z",
    updated_at: "2026-04-09T00:00:00Z",
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
      character_count: null,
      checksum_sha256: "abc",
      created_at: "2026-04-09T00:00:00Z",
      updated_at: "2026-04-09T00:00:00Z",
    },
    draft: null,
  });

  renderPage();

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
});

test("style lab page shows running stage feedback", async () => {
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
  apiMock.getStyleAnalysisJobs.mockResolvedValueOnce([
    {
      id: "job-1",
      style_name: "分析中的任务",
      provider_id: "provider-1",
      model_name: "gpt-4.1-mini",
      status: "running",
      stage: "analyzing",
      error_message: null,
      started_at: "2026-04-09T00:00:00Z",
      completed_at: null,
      created_at: "2026-04-09T00:00:00Z",
      updated_at: "2026-04-09T00:00:00Z",
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
        character_count: 8,
        checksum_sha256: "abc",
        created_at: "2026-04-09T00:00:00Z",
        updated_at: "2026-04-09T00:00:00Z",
      },
      draft: null,
    },
  ]);
  apiMock.getStyleAnalysisJob.mockResolvedValueOnce({
    id: "job-1",
    style_name: "分析中的任务",
    provider_id: "provider-1",
    model_name: "gpt-4.1-mini",
    status: "running",
    stage: "analyzing",
    error_message: null,
    started_at: "2026-04-09T00:00:00Z",
    completed_at: null,
    created_at: "2026-04-09T00:00:00Z",
    updated_at: "2026-04-09T00:00:00Z",
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
      character_count: 8,
      checksum_sha256: "abc",
      created_at: "2026-04-09T00:00:00Z",
      updated_at: "2026-04-09T00:00:00Z",
    },
    draft: null,
  });
  apiMock.getStyleProfiles.mockResolvedValueOnce([]);
  apiMock.getProjects.mockResolvedValueOnce([]);

  renderPage();

  expect(await screen.findByText("当前阶段：analyzing")).toBeInTheDocument();
});

test("style lab page saves edited draft and mounts project", async () => {
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
  apiMock.getStyleAnalysisJobs.mockResolvedValueOnce([
    {
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
      draft: {
        style_name: "旧名字",
        analysis_summary: "短句凌厉。",
        global_system_prompt: "保留凌厉感。",
        dimensions: {
          vocabulary_habits: "偏爱短促动词。",
          syntax_rhythm: "短句为主。",
          narrative_perspective: "第三人称。",
          dialogue_traits: "对白克制。",
        },
        scene_prompts: {
          dialogue: "对白短。",
          action: "动作快。",
          environment: "环境冷。",
        },
        few_shot_examples: [
          { type: "environment", text: "风从长街尽头吹来。" },
          { type: "dialogue", text: "他只说了一句好。" },
        ],
      },
    },
  ]);
  apiMock.getStyleAnalysisJob.mockResolvedValueOnce({
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
    draft: {
      style_name: "旧名字",
      analysis_summary: "短句凌厉。",
      global_system_prompt: "保留凌厉感。",
      dimensions: {
        vocabulary_habits: "偏爱短促动词。",
        syntax_rhythm: "短句为主。",
        narrative_perspective: "第三人称。",
        dialogue_traits: "对白克制。",
      },
      scene_prompts: {
        dialogue: "对白短。",
        action: "动作快。",
        environment: "环境冷。",
      },
      few_shot_examples: [
        { type: "environment", text: "风从长街尽头吹来。" },
        { type: "dialogue", text: "他只说了一句好。" },
      ],
    },
  });
  apiMock.getStyleProfiles.mockResolvedValueOnce([]);
  apiMock.getProjects.mockResolvedValueOnce([
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
    analysis_summary: "短句凌厉。",
    global_system_prompt: "保留凌厉感。",
    dimensions: {
      vocabulary_habits: "偏爱短促动词。",
      syntax_rhythm: "短句为主。",
      narrative_perspective: "第三人称。",
      dialogue_traits: "对白克制。",
    },
    scene_prompts: {
      dialogue: "对白短。",
      action: "动作快。",
      environment: "环境冷。",
    },
    few_shot_examples: [
      { type: "environment", text: "风从长街尽头吹来。" },
      { type: "dialogue", text: "他只说了一句好。" },
    ],
    created_at: "2026-04-09T00:02:00Z",
    updated_at: "2026-04-09T00:02:00Z",
  });
  apiMock.updateProject.mockResolvedValueOnce({
    id: "project-1",
    name: "风格挂载项目",
    description: "项目简介",
    status: "draft",
    default_model: "gpt-4.1-mini",
    style_profile_id: "profile-1",
    archived_at: null,
    provider: {
      id: "provider-1",
      label: "Primary Gateway",
      base_url: "https://api.openai.com/v1",
      default_model: "gpt-4.1-mini",
      is_enabled: true,
    },
  });

  renderPage();

  fireEvent.change(await screen.findByLabelText("风格名称"), {
    target: { value: "新名字" },
  });
  fireEvent.click(screen.getByRole("combobox", { name: "挂载到项目" }));
  fireEvent.click(await screen.findByText("风格挂载项目"));
  fireEvent.click(screen.getByRole("button", { name: "保存并挂载" }));

  await waitFor(() => expect(apiMock.createStyleProfile).toHaveBeenCalledTimes(1));
  await waitFor(() => expect(apiMock.updateProject).toHaveBeenCalledWith("project-1", { style_profile_id: "profile-1" }));
});
