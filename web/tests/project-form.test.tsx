import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import { ProjectForm } from "@/components/project-form";


test("project form lets user select a style profile and submit it", async () => {
  const onSubmit = vi.fn(async () => {});

  render(
    <ProjectForm
      providers={[
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
          created_at: "2026-04-09T00:00:00Z",
          updated_at: "2026-04-09T00:00:00Z",
        },
      ]}
      styleProfiles={[
        {
          id: "profile-1",
          provider_id: "provider-1",
          model_name: "gpt-4.1-mini",
          source_filename: "sample.txt",
          style_name: "午夜霓虹档案",
          created_at: "2026-04-09T00:00:00Z",
          updated_at: "2026-04-09T00:00:00Z",
        },
      ]}
      plotProfiles={[
        {
          id: "plot-1",
          provider_id: "provider-1",
          model_name: "gpt-4.1-mini",
          source_filename: "sample.txt",
          plot_name: "反派修罗场模板",
          created_at: "2026-04-09T00:00:00Z",
          updated_at: "2026-04-09T00:00:00Z",
        },
      ]}
      submitting={false}
      onSubmit={onSubmit}
    />,
  );

  fireEvent.change(screen.getByLabelText("项目名称"), {
    target: { value: "新项目" },
  });
  fireEvent.click(screen.getByRole("combobox", { name: "风格档案" }));
  fireEvent.click(await screen.findByRole("option", { name: "午夜霓虹档案" }));
  fireEvent.click(screen.getByRole("combobox", { name: "情节档案" }));
  fireEvent.click(await screen.findByRole("option", { name: "反派修罗场模板" }));
  fireEvent.click(screen.getByRole("button", { name: "保存项目" }));

  await waitFor(() => expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({
    name: "新项目",
    style_profile_id: "profile-1",
    plot_profile_id: "plot-1",
  })));
});

test("new project page renders the concept gacha component", async () => {
  vi.resetModules();
  vi.doMock("@/components/concept-gacha-page", () => ({
    ConceptGachaPage: ({
      providers,
      styleProfiles,
    }: {
      providers: unknown[];
      styleProfiles: unknown[];
    }) => (
      <div>
        concept-gacha-providers-{providers.length}-styles-{styleProfiles.length}
      </div>
    ),
  }));
  vi.doMock("@/lib/server-api", () => ({
    getServerApi: vi.fn().mockResolvedValue({
      getProviderConfigs: vi.fn().mockResolvedValue([{ id: "p1" }]),
      getStyleProfiles: vi.fn().mockResolvedValue([{ id: "s1" }]),
      getPlotProfiles: vi.fn().mockResolvedValue([{ id: "pplot1" }]),
    }),
  }));

  const { default: NewProjectPage } = await import("@/app/(workspace)/projects/new/page");

  const node = await NewProjectPage();
  render(node);

  expect(screen.getByText("concept-gacha-providers-1-styles-1")).toBeInTheDocument();
});

test("project detail page is a server wrapper around the workbench", async () => {
  vi.resetModules();
  vi.doMock("@/components/project-workbench", () => ({
    ProjectWorkbench: ({ project }: { project: { id: string; name: string } }) => (
      <div>project-workbench-{project.id}</div>
    ),
  }));
  vi.doMock("@/lib/server-api", () => ({
    getServerApi: vi.fn().mockResolvedValue({
      getProject: vi.fn().mockResolvedValue({
        id: "project-42",
        name: "Mock Project",
      }),
      getProviderConfigs: vi.fn().mockResolvedValue([]),
      getStyleProfiles: vi.fn().mockResolvedValue([]),
      getPlotProfiles: vi.fn().mockResolvedValue([]),
    }),
  }));

  const { default: ProjectDetailPage } = await import("@/app/(workspace)/projects/[id]/page");
  const page = await ProjectDetailPage({
    params: Promise.resolve({ id: "project-42" }),
  });

  render(page);

  expect(screen.getByText("project-workbench-project-42")).toBeInTheDocument();
});
