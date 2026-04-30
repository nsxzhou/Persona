import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, vi } from "vitest";

import { StyleLabWizardView } from "@/components/style-lab-wizard-view";

const apiMock = vi.hoisted(() => ({
  getStyleAnalysisJobStatus: vi.fn(),
  getStyleAnalysisJob: vi.fn(),
  getStyleAnalysisJobAnalysisReport: vi.fn(),
  getStyleAnalysisJobVoiceProfile: vi.fn(),
  getStyleProfile: vi.fn(),
  createStyleProfile: vi.fn(),
  updateStyleProfile: vi.fn(),
  resumeStyleAnalysisJob: vi.fn(),
  pauseStyleAnalysisJob: vi.fn(),
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
      <StyleLabWizardView jobId={jobId} />
    </QueryClientProvider>,
  );
}

function buildReport() {
  return "# 执行摘要\n整体文风冷峻、短句密集、留白明显。\n";
}

function buildVoiceProfile() {
  return "# Voice Profile\n## 3.1 口头禅与常用表达\n- 执行规则：短句推进\n";
}

function buildVoiceProfilePayload() {
  return {
    common_expressions: "短句推进",
    sentence_patterns: "长短句交替",
    lexical_preferences: "现代术语与古典四字格混用",
    sentence_construction: "句首落判断",
    personal_scene_clues: "生活线索弱",
    domain_regional_lexicon: "行业词偏运营",
    natural_irregularities: "保留省略和跳接",
    avoided_patterns: "少写解释性开场",
    metaphors_imagery: "意象偏月色与视线",
    logic_and_emotion: "观察、质疑、类比、结论递进",
    dialogue_modes: "对白抢拍试探",
    values_motifs: "强调效率和掌控",
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

beforeEach(() => {
  vi.resetAllMocks();
  apiMock.getStyleAnalysisJobStatus.mockResolvedValue({
    id: "job-1",
    status: "succeeded",
    stage: null,
    error_message: null,
    updated_at: "2026-04-09T00:01:00Z",
  });
  apiMock.getStyleAnalysisJob.mockResolvedValue(buildSucceededJob());
  apiMock.getStyleAnalysisJobAnalysisReport.mockResolvedValue(buildReport());
  apiMock.getStyleAnalysisJobVoiceProfile.mockResolvedValue(buildVoiceProfile());
});

test("style lab wizard advances to voice profile step without fetching projects", async () => {
  renderWizard();

  expect(await screen.findByText(/执行摘要/)).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "审阅完毕，下一步" }));
  expect(await screen.findByLabelText("Voice Profile Markdown")).toBeInTheDocument();
});

test("style lab wizard saves new profile with voice profile markdown", async () => {
  apiMock.createStyleProfile.mockResolvedValueOnce({
    id: "profile-1",
    source_job_id: "job-1",
    provider_id: "provider-1",
    model_name: "gpt-4.1-mini",
    source_filename: "sample.txt",
    style_name: "新名字",
    analysis_report_markdown: buildReport(),
    voice_profile_payload: buildVoiceProfilePayload(),
    voice_profile_markdown: "# Voice Profile\n## 3.1 口头禅与常用表达\n- 新值\n",
    created_at: "2026-04-09T00:02:00Z",
    updated_at: "2026-04-09T00:02:00Z",
  });

  renderWizard();

  fireEvent.click(await screen.findByRole("button", { name: "审阅完毕，下一步" }));
  fireEvent.change(screen.getByLabelText("风格名称"), {
    target: { value: "新名字" },
  });
  fireEvent.change(screen.getByLabelText("Voice Profile Markdown"), {
    target: { value: "# Voice Profile\n## 3.1 口头禅与常用表达\n- 新值\n" },
  });
  fireEvent.click(screen.getByRole("button", { name: "确认 Voice Profile" }));

  await waitFor(() =>
    expect(apiMock.createStyleProfile).toHaveBeenCalledWith(
      expect.objectContaining({
        job_id: "job-1",
        style_name: "新名字",
        voice_profile_markdown: "# Voice Profile\n## 3.1 口头禅与常用表达\n- 新值\n",
      }),
    ),
  );
});

test("style lab profile view allows editing voice profile", async () => {
  apiMock.getStyleProfile.mockResolvedValue({
    id: "profile-1",
    source_job_id: "job-1",
    provider_id: "provider-1",
    model_name: "gpt-4.1-mini",
    source_filename: "sample.txt",
    style_name: "旧名字",
    analysis_report_markdown: buildReport(),
    voice_profile_payload: buildVoiceProfilePayload(),
    voice_profile_markdown: buildVoiceProfile(),
    created_at: "2026-04-09T00:02:00Z",
    updated_at: "2026-04-09T00:02:00Z",
  });
  apiMock.getStyleAnalysisJob.mockResolvedValue(
    buildSucceededJob({
      style_profile_id: "profile-1",
      style_profile: {
        id: "profile-1",
      },
    }),
  );
  apiMock.updateStyleProfile.mockResolvedValueOnce({
    id: "profile-1",
    source_job_id: "job-1",
    provider_id: "provider-1",
    model_name: "gpt-4.1-mini",
    source_filename: "sample.txt",
    style_name: "旧名字",
    analysis_report_markdown: buildReport(),
    voice_profile_payload: {
      ...buildVoiceProfilePayload(),
      common_expressions: "更碎的短句推进",
    },
    voice_profile_markdown: "# Voice Profile\n## 3.1 口头禅与常用表达\n- 更碎的短句推进\n",
    created_at: "2026-04-09T00:02:00Z",
    updated_at: "2026-04-09T00:03:00Z",
  });

  renderWizard();

  expect(await screen.findByText("旧名字")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "编辑档案" }));
  fireEvent.change(await screen.findByLabelText("Voice Profile Markdown"), {
    target: { value: "# Voice Profile\n## 3.1 口头禅与常用表达\n- 更碎的短句推进\n" },
  });
  fireEvent.click(screen.getAllByRole("button", { name: "保存修改" })[0]);

  await waitFor(() =>
    expect(apiMock.updateStyleProfile).toHaveBeenCalledWith(
      "profile-1",
      expect.objectContaining({
        style_name: "旧名字",
        voice_profile_markdown: "# Voice Profile\n## 3.1 口头禅与常用表达\n- 更碎的短句推进\n",
      }),
    ),
  );
});
