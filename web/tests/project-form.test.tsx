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
        },
      ]}
      styleProfiles={[
        {
          id: "profile-1",
          source_job_id: "job-1",
          provider_id: "provider-1",
          model_name: "gpt-4.1-mini",
          source_filename: "sample.txt",
          style_name: "午夜霓虹档案",
          analysis_summary: "总结",
          global_system_prompt: "提示词",
          dimensions: {
            vocabulary_habits: "词汇",
            syntax_rhythm: "节奏",
            narrative_perspective: "视角",
            dialogue_traits: "对白",
          },
          scene_prompts: {
            dialogue: "对白",
            action: "动作",
            environment: "环境",
          },
          few_shot_examples: [
            { type: "environment", text: "例句 1" },
            { type: "dialogue", text: "例句 2" },
          ],
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
