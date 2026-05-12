import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, test, vi } from "vitest";

import {
  PlotLabDashboardPageView,
  StyleLabDashboardPageView,
} from "@/components/lab-dashboard-page-view";
import { plotLabQueryKeys } from "@/lib/plot-lab-query-keys";
import { providerQueryKeys } from "@/lib/provider-query-keys";
import { styleLabQueryKeys } from "@/lib/style-lab-query-keys";
import type { PlotAnalysisJobListItem, ProviderConfig, StyleAnalysisJobListItem } from "@/lib/types";

const apiMock = vi.hoisted(() => ({
  getProviderConfigs: vi.fn(),
  getStyleAnalysisJobs: vi.fn(),
  getPlotAnalysisJobs: vi.fn(),
  deleteStyleAnalysisJob: vi.fn(),
  deletePlotAnalysisJob: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  api: apiMock,
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

const provider: ProviderConfig = {
  id: "provider-1",
  label: "Primary",
  base_url: "https://api.example.test/v1",
  default_model: "gpt-test",
  api_key_hint: "****1234",
  is_enabled: true,
  immersion_prompt_override_enabled: false,
  immersion_system_prompt_suffix: "",
  chat_test_system_prompt: "",
  last_test_status: null,
  last_test_error: null,
  last_tested_at: null,
  created_at: "2026-05-07T00:00:00Z",
  updated_at: "2026-05-07T00:00:00Z",
};

const sampleFile = {
  id: "sample-1",
  original_filename: "sample.txt",
  content_type: "text/plain",
  byte_size: 12,
  character_count: 12,
  checksum_sha256: "abc",
  created_at: "2026-05-07T00:00:00Z",
  updated_at: "2026-05-07T00:00:00Z",
};

const styleJob: StyleAnalysisJobListItem = {
  id: "style-job-1",
  style_name: "首屏风格任务",
  profile_style_name: null,
  provider_id: "provider-1",
  model_name: "gpt-test",
  status: "succeeded",
  stage: null,
  error_message: null,
  started_at: "2026-05-07T00:00:00Z",
  completed_at: "2026-05-07T00:01:00Z",
  created_at: "2026-05-07T00:00:00Z",
  updated_at: "2026-05-07T00:01:00Z",
  provider,
  sample_file: sampleFile,
  style_profile_id: null,
};

const plotJob: PlotAnalysisJobListItem = {
  id: "plot-job-1",
  plot_name: "首屏情节任务",
  profile_plot_name: null,
  provider_id: "provider-1",
  model_name: "gpt-test",
  status: "succeeded",
  stage: null,
  error_message: null,
  started_at: "2026-05-07T00:00:00Z",
  completed_at: "2026-05-07T00:01:00Z",
  created_at: "2026-05-07T00:00:00Z",
  updated_at: "2026-05-07T00:01:00Z",
  provider,
  sample_file: sampleFile,
  plot_profile_id: null,
};

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
}

function renderWithClient(ui: React.ReactElement, queryClient = createTestQueryClient()) {
  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>,
  );
}

describe("Lab dashboard pages", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMock.getProviderConfigs.mockResolvedValue([provider]);
    apiMock.getStyleAnalysisJobs.mockResolvedValue([styleJob]);
    apiMock.getPlotAnalysisJobs.mockResolvedValue([plotJob]);
  });

  test("style lab renders hydrated first page without loading", () => {
    const queryClient = createTestQueryClient();
    queryClient.setQueryData(providerQueryKeys.lists(), [provider]);
    queryClient.setQueryData(styleLabQueryKeys.jobs.list(1), [styleJob]);

    renderWithClient(<StyleLabDashboardPageView />, queryClient);

    expect(screen.queryByText("正在载入 Style Lab...")).not.toBeInTheDocument();
    expect(screen.getByText("首屏风格任务")).toBeInTheDocument();
    expect(apiMock.getStyleAnalysisJobs).not.toHaveBeenCalled();
  });

  test("plot lab renders hydrated first page without loading", () => {
    const queryClient = createTestQueryClient();
    queryClient.setQueryData(providerQueryKeys.lists(), [provider]);
    queryClient.setQueryData(plotLabQueryKeys.jobs.list(1), [plotJob]);

    renderWithClient(<PlotLabDashboardPageView />, queryClient);

    expect(screen.queryByText("正在载入 Plot Lab...")).not.toBeInTheDocument();
    expect(screen.getByText("首屏情节任务")).toBeInTheDocument();
    expect(apiMock.getPlotAnalysisJobs).not.toHaveBeenCalled();
  });
});
