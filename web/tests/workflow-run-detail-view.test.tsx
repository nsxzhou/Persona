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

const traceMarkdown = `# Prompt Trace

| Field | Value |
| --- | --- |
| Run ID | \`run-1\` |
| Calls | 1 |
| Completed calls | 1 |
| Failed calls | 0 |
| Total input chars | 12 |
| Contains truncation marker | no |

## Call summary

| # | Stage | Mode | Model | Input chars | Output chars | Truncated | Error |
| --- | --- | --- | --- | ---: | ---: | --- | --- |
| 1 | generating | immersion | gpt-test | 12 | 2 | no | - |

## Call 1 - generating / immersion

| Field | Value |
| --- | --- |
| Intent | \`selection_rewrite\` |
| Stage | \`generating\` |
| Mode | \`immersion\` |
| Provider | \`Primary\` |
| Provider ID | \`provider-1\` |
| Model | \`gpt-test\` |
| Started at | \`2026-05-07T10:00:00.000+00:00\` |
| Completed at | \`2026-05-07T10:00:00.042+00:00\` |
| Duration | 42 ms |
| Total input chars | 12 |
| System chars | 4 |
| User chars | 8 |
| Output chars | 2 |
| Contains truncation marker | no |

### System message

- Chars: 4
- Contains truncation marker: no

\`\`\`
系统提示
\`\`\`

### User message

- Chars: 8
- Contains truncation marker: no

\`\`\`
用户提示
\`\`\`

### Output excerpt

\`\`\`
OK
\`\`\`
`;

describe("WorkflowRunDetailView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMock.getNovelWorkflow.mockResolvedValue(run);
    apiMock.getNovelWorkflowArtifact.mockResolvedValue(traceMarkdown);
    apiMock.getNovelWorkflowLogs.mockResolvedValue({
      content: "[Workflow] ok\n",
      next_offset: 14,
      truncated: false,
    });
  });

  test("renders structured prompt trace by default and copies raw markdown", async () => {
    renderWithClient(<WorkflowRunDetailView runId="run-1" />);

    expect(await screen.findByRole("heading", { name: /局部改写 \/ Prompt Trace/ })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Trace Summary" })).toBeInTheDocument();
    expect(screen.getAllByText("Failed calls").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Total input chars").length).toBeGreaterThan(0);
    expect(screen.getByText("Call 1")).toBeInTheDocument();
    expect(screen.getByText(/input 12 chars/)).toBeInTheDocument();
    expect(screen.getByText("System message")).toBeInTheDocument();
    expect(screen.getByText("User message")).toBeInTheDocument();
    expect(screen.getByText("Output excerpt")).toBeInTheDocument();
    expect(screen.getByText("展开精确数据")).toBeInTheDocument();
    expect(screen.getByText("系统提示")).not.toBeVisible();
    expect(screen.queryByRole("columnheader", { name: "Model" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "复制全文" }));

    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(traceMarkdown);
    });
  });

  test("renders structured prompt trace when fenced content contains headings", async () => {
    const traceWithInnerHeadings = traceMarkdown.replace(
      "系统提示",
      "系统提示\n\n### inner heading\n\n## Call fake - x / y",
    );
    apiMock.getNovelWorkflowArtifact.mockResolvedValue(traceWithInnerHeadings);

    renderWithClient(<WorkflowRunDetailView runId="run-1" />);

    expect(await screen.findByRole("heading", { name: "Trace Summary" })).toBeInTheDocument();
    expect(screen.getByText("Call 1")).toBeInTheDocument();
    fireEvent.click(screen.getByText("System message"));
    expect(
      screen.getByText(
        (_, element) =>
          element?.tagName.toLowerCase() === "pre" &&
          element.textContent?.includes("### inner heading") === true &&
          element.textContent.includes("## Call fake - x / y"),
      ),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(
        (_, element) =>
          element?.tagName.toLowerCase() === "pre" &&
          element.textContent === traceWithInnerHeadings,
      ),
    ).not.toBeInTheDocument();
  });

  test("expands segments and copies individual segment text", async () => {
    renderWithClient(<WorkflowRunDetailView runId="run-1" />);

    expect(await screen.findByText("Call 1")).toBeInTheDocument();
    fireEvent.click(screen.getByText("System message"));

    expect(screen.getByText("系统提示")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "复制 System message" }));

    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith("系统提示");
    });
  });

  test("keeps secondary call metadata hidden until precision data is expanded", async () => {
    renderWithClient(<WorkflowRunDetailView runId="run-1" />);

    expect(await screen.findByText("Call 1")).toBeInTheDocument();
    expect(screen.getByText("provider-1")).not.toBeVisible();

    fireEvent.click(screen.getByText("展开精确数据"));

    expect(screen.getByText("provider-1")).toBeVisible();
  });

  test("falls back to raw markdown when rendered parser fails", async () => {
    apiMock.getNovelWorkflowArtifact.mockResolvedValue("# Prompt Trace\n\n## Call 1");

    renderWithClient(<WorkflowRunDetailView runId="run-1" />);

    expect(
      await screen.findByText(
        (_, element) =>
          element?.tagName.toLowerCase() === "pre" &&
          element.textContent === "# Prompt Trace\n\n## Call 1",
      ),
    ).toBeInTheDocument();
  });

  test("shows empty trace fallback", async () => {
    apiMock.getNovelWorkflowArtifact.mockResolvedValue("");

    renderWithClient(<WorkflowRunDetailView runId="run-1" />);

    expect(await screen.findByText(/当前 run 暂无 Prompt Trace/)).toBeInTheDocument();
  });
});
