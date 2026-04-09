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
          analysis_report: {
            executive_summary: {
              summary: "总结",
              representative_evidence: [{ excerpt: "例句 1", location: "段落 1" }],
            },
            basic_assessment: {
              text_type: "章节正文",
              multi_speaker: false,
              batch_mode: false,
              location_indexing: "章节或段落位置",
              noise_handling: "未发现显著噪声。",
            },
            sections: [],
            appendix: null,
          },
          style_summary: {
            style_name: "午夜霓虹档案",
            style_positioning: "总结",
            core_features: ["词汇"],
            lexical_preferences: ["词汇"],
            rhythm_profile: ["节奏"],
            punctuation_profile: ["标点"],
            imagery_and_themes: ["意象"],
            scene_strategies: [{ scene: "dialogue", instruction: "对白" }],
            avoid_or_rare: ["避免项"],
            generation_notes: ["注意事项"],
          },
          prompt_pack: {
            system_prompt: "提示词",
            scene_prompts: {
              dialogue: "对白",
              action: "动作",
              environment: "环境",
            },
            hard_constraints: ["约束"],
            style_controls: {
              tone: "语气",
              rhythm: "节奏",
              evidence_anchor: "证据",
            },
            few_shot_slots: [
              { label: "environment", type: "environment", text: "例句 1", purpose: "作用 1" },
              { label: "dialogue", type: "dialogue", text: "例句 2", purpose: "作用 2" },
            ],
          },
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
