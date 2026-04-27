import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { WorkbenchTabs } from "@/components/workbench-tabs";

const apiMock = vi.hoisted(() => ({
  getProjectChapters: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  api: apiMock,
}));

vi.mock("@/lib/sse", () => ({
  consumeTextEventStream: vi.fn(),
}));

vi.mock("@/components/bible-tab-content", () => ({
  BibleTabContent: () => <div>bible-tab-content</div>,
}));

vi.mock("@/components/outline-detail-tab", () => ({
  OutlineDetailTab: () => <div>outline-detail-tab</div>,
}));

vi.mock("@/components/settings-tab", () => ({
  SettingsTab: () => <div>settings-tab</div>,
}));

vi.mock("@/components/regenerate-dialog", () => ({
  RegenerateDialog: () => null,
}));

vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
    info: vi.fn(),
  },
}));

const project = {
  id: "project-1",
  name: "Mock Project",
  description: "",
  status: "draft",
  default_provider_id: "provider-1",
  default_model: "gpt-4.1-mini",
  style_profile_id: null,
  plot_profile_id: null,
  inspiration: "",
  world_building: "",
  characters_blueprint: "",
  characters_status: "",
  outline_master: "",
  outline_detail: "",
  runtime_state: "",
  runtime_threads: "",
  length_preset: "short",
  auto_sync_memory: false,
  archived_at: null,
  created_at: "2026-04-10T00:00:00Z",
  updated_at: "2026-04-10T00:00:00Z",
  provider: null,
} as const;

const projectBible = {
  id: "project-1",
  project_id: "project-1",
  inspiration: "Inspiration content",
  world_building: "World building content",
  characters_blueprint: "Characters content",
  characters_status: "",
  outline_master: "Outline master content",
  outline_detail: "Outline detail content",
  runtime_state: "",
  runtime_threads: "",
  created_at: "2026-04-10T00:00:00Z",
  updated_at: "2026-04-10T00:00:00Z",
};

describe("WorkbenchTabs", () => {
  beforeEach(() => {
    apiMock.getProjectChapters.mockReset();
  });

  test("shows a retry affordance when chapter loading fails", async () => {
    apiMock.getProjectChapters.mockRejectedValueOnce(new Error("加载章节失败"));

    render(
      <WorkbenchTabs
        project={project as never}
        projectBible={projectBible as never}
        providers={[]}
        styleProfiles={[]}
        plotProfiles={[]}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText("加载章节失败")).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "重试加载章节" })).toBeInTheDocument();
  });

  it("retries chapter loading after a failure", async () => {
    apiMock.getProjectChapters
      .mockRejectedValueOnce(new Error("Network Error"))
      .mockResolvedValueOnce([]);

    render(
      <WorkbenchTabs
        project={project as never}
        projectBible={projectBible as never}
        providers={[]}
        styleProfiles={[]}
        plotProfiles={[]}
      />,
    );

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "重试加载章节" })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: "重试加载章节" }));

    await waitFor(() => {
      expect(apiMock.getProjectChapters).toHaveBeenCalledTimes(2);
    });
  });
});
