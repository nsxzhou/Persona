import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { NovelWorkflowRunPanel } from "@/components/novel-workflow-run-panel";
import type { NovelWorkflowListItem, NovelWorkflowStatusSnapshot } from "@/lib/types";

const apiMock = vi.hoisted(() => ({
  getNovelWorkflowStatus: vi.fn(),
  getNovelWorkflowLogs: vi.fn(),
  getNovelWorkflowArtifact: vi.fn(),
  pauseNovelWorkflow: vi.fn(),
  resumeNovelWorkflow: vi.fn(),
  decideNovelWorkflow: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  api: apiMock,
}));

const run: NovelWorkflowListItem = {
  id: "run-1",
  intent_type: "chapter_write",
  project_id: "project-1",
  chapter_id: "chapter-1",
  provider_id: "provider-1",
  model_name: "model-1",
  status: "paused",
  stage: "waiting_decision",
  checkpoint_kind: "beats",
  latest_artifacts: ["beats_markdown"],
  warnings: ["节拍长度偏短"],
  error_message: null,
  started_at: null,
  completed_at: null,
  created_at: "2026-04-27T00:00:00Z",
  updated_at: "2026-04-27T00:00:00Z",
  pause_requested_at: null,
};

const pausedStatus: NovelWorkflowStatusSnapshot = {
  id: "run-1",
  status: "paused",
  stage: "waiting_decision",
  checkpoint_kind: "beats",
  latest_artifacts: ["beats_markdown"],
  warnings: ["节拍长度偏短"],
  error_message: null,
  updated_at: "2026-04-27T00:00:00Z",
  pause_requested_at: null,
};

describe("NovelWorkflowRunPanel", () => {
  test("shows run status, warnings, logs and artifacts", async () => {
    apiMock.getNovelWorkflowStatus.mockResolvedValue(pausedStatus);
    apiMock.getNovelWorkflowLogs.mockResolvedValue({
      content: "[Workflow] waiting for beats approval",
      next_offset: 38,
      truncated: false,
    });
    apiMock.getNovelWorkflowArtifact.mockResolvedValue("## Beats\n- 第一拍");

    render(<NovelWorkflowRunPanel run={run} />);

    expect(screen.getByText("工作流 run")).toBeInTheDocument();
    expect(screen.getByText("chapter_write")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("paused")).toBeInTheDocument();
      expect(screen.getByText("waiting_decision")).toBeInTheDocument();
      expect(screen.getByText("beats")).toBeInTheDocument();
      expect(screen.getByText("节拍长度偏短")).toBeInTheDocument();
      expect(screen.getByText("[Workflow] waiting for beats approval")).toBeInTheDocument();
      expect(screen.getByLabelText("beats_markdown 产物内容")).toHaveValue("## Beats\n- 第一拍");
    });
  });

  test("submits approve and revise decisions for paused checkpoints", async () => {
    apiMock.getNovelWorkflowStatus.mockResolvedValue(pausedStatus);
    apiMock.getNovelWorkflowLogs.mockResolvedValue({ content: "", next_offset: 0, truncated: false });
    apiMock.getNovelWorkflowArtifact.mockResolvedValue("## Beats\n- 第一拍");
    apiMock.decideNovelWorkflow.mockResolvedValue({
      ...pausedStatus,
      status: "pending",
      stage: null,
      checkpoint_kind: null,
    });

    render(<NovelWorkflowRunPanel run={run} />);

    await waitFor(() => {
      expect(screen.getByLabelText("beats_markdown 产物内容")).toHaveValue("## Beats\n- 第一拍");
    });
    fireEvent.click(screen.getByRole("button", { name: "批准继续" }));

    await waitFor(() => {
      expect(apiMock.decideNovelWorkflow).toHaveBeenCalledWith("run-1", {
      action: "approve",
      artifact_name: "beats_markdown",
      edited_markdown: "## Beats\n- 第一拍",
      });
    });

    apiMock.decideNovelWorkflow.mockClear();
    apiMock.getNovelWorkflowStatus.mockResolvedValue(pausedStatus);
    fireEvent.click(screen.getByRole("button", { name: "刷新" }));
    await screen.findByLabelText("修订意见");
    fireEvent.change(screen.getByLabelText("beats_markdown 产物内容"), {
      target: { value: "## Beats\n- 修改后的第一拍" },
    });
    fireEvent.change(screen.getByLabelText("修订意见"), {
      target: { value: "加重章末钩子" },
    });
    fireEvent.click(screen.getByRole("button", { name: "提交修订" }));

    await waitFor(() => {
      expect(apiMock.decideNovelWorkflow).toHaveBeenLastCalledWith("run-1", {
        action: "revise",
        artifact_name: "beats_markdown",
        edited_markdown: "## Beats\n- 修改后的第一拍",
        feedback: "加重章末钩子",
      });
    });
  });
});
