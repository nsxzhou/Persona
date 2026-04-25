import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { SettingsTab } from "@/components/settings-tab";

const updateProjectActionMock = vi.fn();

vi.mock("@tanstack/react-query", () => ({
  useMutation: ({ mutationFn }: { mutationFn: (payload: Record<string, unknown>) => Promise<unknown> }) => ({
    isPending: false,
    mutate: (payload: Record<string, unknown>) => {
      void mutationFn(payload);
    },
  }),
}));

vi.mock("@/app/(workspace)/projects/actions", () => ({
  updateProjectAction: (...args: unknown[]) => updateProjectActionMock(...args),
}));

vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

describe("SettingsTab", () => {
  test("submits generation_profile in save payload", () => {
    updateProjectActionMock.mockResolvedValue({});

    const project = {
      id: "project-1",
      name: "项目A",
      description: "desc",
      status: "draft",
      default_provider_id: "provider-1",
      default_model: "model-1",
      style_profile_id: null,
      plot_profile_id: null,
      generation_profile: {
        genre_mother: "urban",
        desire_overlays: ["harem_collect"],
        intensity_level: "edge",
        pov_mode: "limited_third",
        morality_axis: "gray_pragmatism",
        pace_density: "balanced",
      },
      provider: { id: "provider-1", label: "Provider", default_model: "model-1", is_enabled: true },
    };

    render(
      <SettingsTab
        project={project as never}
        providers={[project.provider] as never}
        styleProfiles={[]}
        plotProfiles={[]}
      />,
    );

    expect(screen.getByText("生成策略（Generation Profile）")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "保存配置" }));

    expect(updateProjectActionMock).toHaveBeenCalledWith(
      "project-1",
      expect.objectContaining({
        generation_profile: {
          genre_mother: "urban",
          desire_overlays: ["harem_collect"],
          intensity_level: "edge",
          pov_mode: "limited_third",
          morality_axis: "gray_pragmatism",
          pace_density: "balanced",
        },
      }),
    );
  });
});
