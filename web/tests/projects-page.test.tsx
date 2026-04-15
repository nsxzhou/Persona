import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

import { ProjectsPageView } from "@/components/projects-page-view";


test("projects page renders active projects and archive toggle", () => {
  render(
    <ProjectsPageView
      includeArchived={false}
      onIncludeArchivedChange={vi.fn()}
      page={1}
      hasNextPage={false}
      onPageChange={vi.fn()}
      projects={[
        {
          id: "project-1",
          name: "Immortal River Chronicle",
          description: "东方玄幻长篇项目",
          status: "active",
          default_provider_id: "provider-1",
          default_model: "gpt-4.1-mini",
          style_profile_id: null,
          inspiration: "",
          world_building: "",
          characters: "",
          outline_master: "",
          outline_detail: "",
          story_bible: "",
          content: "",
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
      ]}
    />,
  );

  expect(screen.getByText("项目管理")).toBeInTheDocument();
  expect(screen.getByText("Immortal River Chronicle")).toBeInTheDocument();
  expect(screen.getByLabelText("显示已归档")).toBeInTheDocument();
});

test("projects page is a server wrapper around the projects client container", async () => {
  vi.resetModules();
  vi.doMock("@/components/projects-page-view", () => ({
    ProjectsPageClient: () => <div>projects-client-container</div>,
    ProjectsPageView: () => null,
  }));

  const { default: ProjectsPage } = await import("@/app/(workspace)/projects/page");

  render(<ProjectsPage />);

  expect(screen.getByText("projects-client-container")).toBeInTheDocument();
});
