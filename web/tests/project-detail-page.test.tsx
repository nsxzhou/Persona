import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

vi.mock("@/lib/server-api", () => ({
  getServerApi: vi.fn().mockResolvedValue({
    getProject: vi.fn().mockResolvedValue({
      id: "project-1",
      name: "反派攻略手册",
      description: "",
      status: "active",
      default_provider_id: "provider-1",
      default_model: "gpt-4.1-mini",
      style_profile_id: "style-1",
      inspiration: "",
      world_building: "",
      characters: "",
      outline_master: "",
      outline_detail: "",
      runtime_state: "",
      runtime_threads: "",
      length_preset: "short",
      archived_at: null,
      created_at: "2026-04-10T00:00:00Z",
      updated_at: "2026-04-10T00:00:00Z",
    }),
    getProviderConfigs: vi.fn().mockResolvedValue([]),
    getStyleProfiles: vi.fn().mockResolvedValue([]),
    getPlotProfiles: vi.fn().mockResolvedValue([]),
  }),
}));

vi.mock("@/components/project-workbench", () => ({
  ProjectWorkbench: (props: Record<string, unknown>) => (
    <div>
      <div>project-workbench</div>
      <div>{String(props.initialTab)}</div>
      <div>{String(props.highlightedVolumeIndex)}</div>
    </div>
  ),
}));

describe("ProjectDetailPage", () => {
  test("passes tab and target volume from search params into the workbench", async () => {
    const ProjectDetailPage = (await import("@/app/(workspace)/projects/[id]/page")).default;

    render(
      await ProjectDetailPage({
        params: Promise.resolve({ id: "project-1" }),
        searchParams: Promise.resolve({
          tab: "outline_detail",
          volumeIndex: "2",
        }),
      } as never),
    );

    expect(screen.getByText("project-workbench")).toBeInTheDocument();
    expect(screen.getByText("outline_detail")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
  });
});

describe("server auth handling", () => {
  test("project detail page does not collapse non-401 server-api failures into logged-out state", async () => {
    vi.resetModules();
    vi.doMock("@/lib/server-api", () => ({
      getServerApi: vi.fn().mockRejectedValue(Object.assign(new Error("boom"), { status: 500 })),
    }));

    const ProjectDetailPage = (await import("@/app/(workspace)/projects/[id]/page")).default;

    await expect(
      ProjectDetailPage({
        params: Promise.resolve({ id: "project-1" }),
        searchParams: Promise.resolve({}),
      } as never),
    ).rejects.toThrow("boom");
  });
});
