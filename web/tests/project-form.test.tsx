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
      submitting={false}
      onSubmit={onSubmit}
    />,
  );

  fireEvent.change(screen.getByLabelText("项目名称"), {
    target: { value: "新项目" },
  });
  fireEvent.click(screen.getByRole("combobox", { name: "风格档案" }));
  fireEvent.click(await screen.findByRole("option", { name: "午夜霓虹档案" }));
  fireEvent.click(screen.getByRole("button", { name: "保存项目" }));

  await waitFor(() => expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({
    name: "新项目",
    style_profile_id: "profile-1",
  })));
});

test("new project page is a server wrapper around the new-project client container", async () => {
  vi.resetModules();
  vi.doMock("@/components/project-form", () => ({
    ProjectPageClient: ({ mode, projectId }: { mode: "new" | "detail"; projectId?: string }) => (
      <div>project-page-client-{mode}-{projectId ?? "none"}</div>
    ),
    ProjectForm: () => null,
  }));

  const { default: NewProjectPage } = await import("@/app/(workspace)/projects/new/page");

  render(<NewProjectPage />);

  expect(screen.getByText("project-page-client-new-none")).toBeInTheDocument();
});

test("project detail page is a server wrapper around the detail client container", async () => {
  vi.resetModules();
  vi.doMock("@/components/project-form", () => ({
    ProjectPageClient: ({ mode, projectId }: { mode: "new" | "detail"; projectId?: string }) => (
      <div>project-page-client-{mode}-{projectId ?? "none"}</div>
    ),
    ProjectForm: () => null,
  }));

  const { default: ProjectDetailPage } = await import("@/app/(workspace)/projects/[id]/page");
  const page = await ProjectDetailPage({
    params: Promise.resolve({ id: "project-42" }),
  });

  render(page);

  expect(screen.getByText("project-page-client-detail-project-42")).toBeInTheDocument();
});
