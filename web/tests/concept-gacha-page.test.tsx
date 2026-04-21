import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { ConceptGachaPage } from "@/components/concept-gacha-page";

const {
  replaceMock,
  generateConceptsMock,
  createProjectActionMock,
} = vi.hoisted(() => ({
  replaceMock: vi.fn(),
  generateConceptsMock: vi.fn(),
  createProjectActionMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    replace: replaceMock,
  }),
}));

vi.mock("@/lib/api", () => ({
  api: {
    generateConcepts: generateConceptsMock,
  },
}));

vi.mock("@/app/(workspace)/projects/actions", () => ({
  createProjectAction: createProjectActionMock,
}));

describe("ConceptGachaPage", () => {
  beforeEach(() => {
    replaceMock.mockReset();
    generateConceptsMock.mockReset();
    createProjectActionMock.mockReset();
  });

  test("passes selected style profile when creating a project from a concept", async () => {
    generateConceptsMock.mockResolvedValue({
      concepts: [
        {
          title: "纸上王朝",
          synopsis: "一段足够长的项目简介，用于创建项目。",
        },
      ],
    });
    createProjectActionMock.mockResolvedValue({ id: "project-1" });

    render(
      <ConceptGachaPage
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
      />,
    );

    fireEvent.change(screen.getByLabelText("你的灵感"), {
      target: { value: "一个被迫冒名顶替入局的寒门书生。" },
    });
    fireEvent.click(screen.getByRole("button", { name: "生成标题和简介" }));

    expect(generateConceptsMock).toHaveBeenCalledWith(
      {
        inspiration: "一个被迫冒名顶替入局的寒门书生。",
        provider_id: "provider-1",
        model: null,
        count: 3,
      },
      undefined,
    );

    await screen.findByRole("button", { name: /纸上王朝/ });
    fireEvent.click(screen.getByRole("button", { name: /纸上王朝/ }));

    fireEvent.click(screen.getByRole("combobox", { name: "风格档案" }));
    fireEvent.click(await screen.findByRole("option", { name: "午夜霓虹档案" }));
    fireEvent.click(screen.getByRole("combobox", { name: "情节档案" }));
    fireEvent.click(await screen.findByRole("option", { name: "反派修罗场模板" }));

    fireEvent.click(screen.getByRole("button", { name: "确认选择" }));

    await waitFor(() =>
      expect(createProjectActionMock).toHaveBeenCalledWith(
        expect.objectContaining({
          name: "纸上王朝",
          description: "一段足够长的项目简介，用于创建项目。",
          style_profile_id: "profile-1",
          plot_profile_id: "plot-1",
        }),
      ),
    );
    expect(replaceMock).toHaveBeenCalledWith("/projects/project-1");
  });
});
