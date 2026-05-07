import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { WorkflowRunDetailView } from "@/components/workflow-run-detail-view";
import type { NovelWorkflow } from "@/lib/types";

const apiMock = vi.hoisted(() => ({
  getNovelWorkflow: vi.fn(),
  getNovelWorkflowArtifact: vi.fn(),
  getNovelWorkflowLogs: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  api: apiMock,
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    message: vi.fn(),
    error: vi.fn(),
  },
}));

Object.assign(navigator, {
  clipboard: {
    writeText: vi.fn().mockResolvedValue(undefined),
  },
});

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

const run: NovelWorkflow = {
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
  latest_artifacts: ["prose_markdown"],
  warnings: [],
  error_message: null,
  started_at: "2026-05-07T01:00:00Z",
  completed_at: "2026-05-07T01:00:01Z",
  created_at: "2026-05-07T01:00:00Z",
  updated_at: "2026-05-07T01:00:01Z",
  pause_requested_at: null,
  request_payload: { intent_type: "selection_rewrite" },
  decision_payload: null,
};

describe("WorkflowRunDetailView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMock.getNovelWorkflow.mockResolvedValue(run);
    apiMock.getNovelWorkflowArtifact.mockResolvedValue("# Prompt Trace\n\n## Call 1");
    apiMock.getNovelWorkflowLogs.mockResolvedValue({
      content: "[Workflow] ok\n",
      next_offset: 14,
      truncated: false,
    });
  });

  test("renders prompt trace and copies raw markdown", async () => {
    renderWithClient(<WorkflowRunDetailView runId="run-1" />);

    expect(await screen.findByRole("heading", { name: /局部改写 \/ Prompt Trace/ })).toBeInTheDocument();
    expect(
      await screen.findByText(
        (_, element) =>
          element?.tagName.toLowerCase() === "pre" &&
          element.textContent === "# Prompt Trace\n\n## Call 1",
      ),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "复制全文" }));

    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith("# Prompt Trace\n\n## Call 1");
    });
  });

  test("shows empty trace fallback", async () => {
    apiMock.getNovelWorkflowArtifact.mockResolvedValue("");

    renderWithClient(<WorkflowRunDetailView runId="run-1" />);

    expect(await screen.findByText(/当前 run 暂无 Prompt Trace/)).toBeInTheDocument();
  });
});
