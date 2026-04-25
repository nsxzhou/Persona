import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

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
      getProjectBible: vi.fn().mockResolvedValue({
        id: "project-1",
        project_id: "project-1",
        inspiration: "",
        world_building: "",
        characters: "",
        outline_master: "",
        outline_detail: "",
        runtime_state: "",
        runtime_threads: "",
        created_at: "2026-04-10T00:00:00Z",
        updated_at: "2026-04-10T00:00:00Z",
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
