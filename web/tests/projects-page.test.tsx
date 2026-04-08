import { render, screen } from "@testing-library/react";

import { ProjectsPageView } from "@/components/projects-page-view";


test("projects page renders active projects and archive toggle", () => {
  render(
    <ProjectsPageView
      includeArchived={false}
      onIncludeArchivedChange={() => {}}
      projects={[
        {
          id: "project-1",
          name: "Immortal River Chronicle",
          description: "东方玄幻长篇项目",
          status: "active",
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
      ]}
    />,
  );

  expect(screen.getByText("项目管理")).toBeInTheDocument();
  expect(screen.getByText("Immortal River Chronicle")).toBeInTheDocument();
  expect(screen.getByLabelText("显示已归档")).toBeInTheDocument();
});

