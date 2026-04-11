import type { components } from "@/lib/api/generated/openapi";
import { promptPackSchema, styleSummarySchema } from "@/lib/validations/style-lab";

type StyleSummaryContract = components["schemas"]["StyleSummary"];
type PromptPackContract = components["schemas"]["PromptPack"];

test("style summary schema accepts OpenAPI-generated contract values", () => {
  const summary: StyleSummaryContract = {
    style_name: "冷白风",
    style_positioning: "短句、克制、冷感。",
    core_features: ["短句推进"],
    lexical_preferences: ["忽然"],
    rhythm_profile: ["停顿明显"],
    punctuation_profile: ["句号收束"],
    imagery_and_themes: ["夜色"],
    scene_strategies: [{ scene: "dialogue", instruction: "对白尽量短。" }],
    avoid_or_rare: ["避免抒情堆砌"],
    generation_notes: ["保留高置信特征"],
  };

  expect(styleSummarySchema.parse(summary)).toEqual(summary);
});

test("prompt pack schema accepts OpenAPI-generated contract values", () => {
  const promptPack: PromptPackContract = {
    system_prompt: "以冷峻中文小说文风进行创作。",
    scene_prompts: {
      dialogue: "对白短促。",
      action: "动作利落。",
      environment: "环境服务情绪。",
    },
    hard_constraints: ["避免网络口吻"],
    style_controls: {
      tone: "冷峻克制",
      rhythm: "短句驱动",
      evidence_anchor: "优先保留高置信特征",
    },
    few_shot_slots: [
      {
        label: "environment",
        type: "environment",
        text: "夜色像一把薄刀。",
        purpose: "建立冷感氛围",
      },
    ],
  };

  expect(promptPackSchema.parse(promptPack)).toEqual(promptPack);
});
