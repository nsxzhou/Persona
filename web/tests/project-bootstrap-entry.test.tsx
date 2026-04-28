import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { ProjectWorkbench } from "@/components/project-workbench";

const {
  refreshMock,
  apiMock,
  updateProjectActionMock,
} = vi.hoisted(() => ({
  refreshMock: vi.fn(),
  apiMock: {
    getProjectBible: vi.fn(),
    runProjectBootstrapWorkflow: vi.fn(),
    getNovelWorkflowArtifact: vi.fn(),
    decideNovelWorkflow: vi.fn(),
    waitForNovelWorkflow: vi.fn(),
  },
  updateProjectActionMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    refresh: refreshMock,
  }),
}));

vi.mock("@/lib/api", () => ({
  api: apiMock,
}));

vi.mock("@/app/(workspace)/projects/actions", () => ({
  updateProjectAction: (...args: unknown[]) => updateProjectActionMock(...args),
}));

vi.mock("@/components/workbench-tabs", () => ({
  WorkbenchTabs: () => <div data-testid="workbench-tabs" />,
}));

vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
    info: vi.fn(),
    success: vi.fn(),
  },
}));

const project = {
  id: "project-1",
  name: "空白项目",
  description: "来自 Concept Gacha 的简介允许存在",
  status: "draft",
  default_provider_id: null,
  default_model: null,
  style_profile_id: null,
  plot_profile_id: null,
  generation_profile: null,
  archived_at: null,
  created_at: "2026-04-27T00:00:00Z",
  updated_at: "2026-04-27T00:00:00Z",
  provider: null,
};

const blankBible = {
  id: "bible-1",
  project_id: "project-1",
  inspiration: "",
  world_building: "",
  characters_blueprint: "",
  characters_status: "",
  outline_master: "",
  outline_detail: "",
  runtime_state: "",
  runtime_threads: "",
  created_at: "2026-04-27T00:00:00Z",
  updated_at: "2026-04-27T00:00:00Z",
};

const renderWorkbench = (projectBible = blankBible) =>
  render(
    <ProjectWorkbench
      project={project as never}
      projectBible={projectBible as never}
      providers={[]}
      styleProfiles={[]}
      plotProfiles={[]}
    />,
  );

describe("ProjectWorkbench project bootstrap entry", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMock.getProjectBible.mockResolvedValue(blankBible);
    apiMock.runProjectBootstrapWorkflow.mockResolvedValue({
      run: { id: "run-1" },
      status: {
        id: "run-1",
        status: "paused",
        stage: "review_outline_bundle",
        checkpoint_kind: "outline_bundle",
        latest_artifacts: ["outline_bundle"],
        warnings: [],
        error_message: null,
        updated_at: "2026-04-27T00:00:00Z",
        pause_requested_at: "2026-04-27T00:00:01Z",
      },
    });
    apiMock.getNovelWorkflowArtifact.mockResolvedValue("# Outline Bundle\n\n原始大纲");
    apiMock.decideNovelWorkflow.mockResolvedValue({
      id: "run-1",
      status: "running",
      checkpoint_kind: null,
      latest_artifacts: [],
      warnings: [],
      error_message: null,
      updated_at: "2026-04-27T00:00:02Z",
      pause_requested_at: null,
    });
    apiMock.waitForNovelWorkflow.mockResolvedValue({
      id: "run-1",
      status: "succeeded",
      checkpoint_kind: null,
      latest_artifacts: ["project_bible"],
      warnings: [],
      error_message: null,
      updated_at: "2026-04-27T00:00:03Z",
      pause_requested_at: null,
    });
  });

  test("shows the project bootstrap button for a blank Bible", () => {
    renderWorkbench();

    expect(screen.getByRole("button", { name: "一键初始化 (AI)" })).toBeEnabled();
  });

  test("disables the project bootstrap button when any Bible field has content", () => {
    renderWorkbench({
      ...blankBible,
      outline_master: "已有主线大纲",
    });

    expect(screen.getByRole("button", { name: "一键初始化 (AI)" })).toBeDisabled();
  });

  test("opens outline bundle review after starting a paused project bootstrap workflow", async () => {
    renderWorkbench();

    fireEvent.click(screen.getByRole("button", { name: "一键初始化 (AI)" }));

    await screen.findByText("项目初始化审核");

    expect(apiMock.getProjectBible).toHaveBeenCalledWith("project-1");
    expect(apiMock.runProjectBootstrapWorkflow).toHaveBeenCalledWith("project-1");
    expect(apiMock.getNovelWorkflowArtifact).toHaveBeenCalledWith("run-1", "outline_bundle");
    expect(screen.getByRole("textbox")).toHaveValue("# Outline Bundle\n\n原始大纲");
  });

  test("approves the outline bundle and refreshes after the workflow succeeds", async () => {
    renderWorkbench();

    fireEvent.click(screen.getByRole("button", { name: "一键初始化 (AI)" }));
    await screen.findByText("项目初始化审核");
    fireEvent.click(screen.getByRole("button", { name: "直接通过" }));

    await waitFor(() => {
      expect(apiMock.decideNovelWorkflow).toHaveBeenCalledWith("run-1", {
        action: "approve",
        artifact_name: "outline_bundle",
      });
    });
    expect(apiMock.waitForNovelWorkflow).toHaveBeenCalledWith("run-1");
    expect(refreshMock).toHaveBeenCalled();
  });

  test("submits edited outline bundle revisions and refreshes after the workflow succeeds", async () => {
    renderWorkbench();

    fireEvent.click(screen.getByRole("button", { name: "一键初始化 (AI)" }));
    await screen.findByText("项目初始化审核");
    const editor = screen.getByRole("textbox");
    expect(editor).toHaveValue("# Outline Bundle\n\n原始大纲");
    fireEvent.change(editor, {
      target: { value: "# Outline Bundle\n\n修改后的大纲" },
    });
    fireEvent.click(screen.getByRole("button", { name: "使用修改版通过" }));

    await waitFor(() => {
      expect(apiMock.decideNovelWorkflow).toHaveBeenCalledWith("run-1", {
        action: "revise",
        artifact_name: "outline_bundle",
        edited_markdown: "# Outline Bundle\n\n修改后的大纲",
      });
    });
    expect(apiMock.waitForNovelWorkflow).toHaveBeenCalledWith("run-1");
    expect(refreshMock).toHaveBeenCalled();
  });
});
