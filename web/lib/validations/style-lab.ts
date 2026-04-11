import { z } from "zod";
import type { PromptPack, StyleSummary } from "@/lib/types";

type AssertExtends<T extends U, U> = true;

const styleSummarySceneStrategySchema = z.object({
  scene: z.string().min(1),
  instruction: z.string().min(1),
});

export const styleSummarySchema = z.object({
  style_name: z.string().min(1),
  style_positioning: z.string().min(1),
  core_features: z.array(z.string().min(1)).min(1),
  lexical_preferences: z.array(z.string()),
  rhythm_profile: z.array(z.string()),
  punctuation_profile: z.array(z.string()),
  imagery_and_themes: z.array(z.string()),
  scene_strategies: z.array(styleSummarySceneStrategySchema),
  avoid_or_rare: z.array(z.string()),
  generation_notes: z.array(z.string()),
});

const scenePromptsSchema = z.object({
  dialogue: z.string(),
  action: z.string(),
  environment: z.string(),
});

const styleControlsSchema = z.object({
  tone: z.string(),
  rhythm: z.string(),
  evidence_anchor: z.string(),
});

const fewShotSlotSchema = z.object({
  label: z.string(),
  type: z.string(),
  purpose: z.string(),
  text: z.string(),
});

export const promptPackSchema = z.object({
  system_prompt: z.string(),
  scene_prompts: scenePromptsSchema,
  hard_constraints: z.array(z.string()),
  style_controls: styleControlsSchema,
  few_shot_slots: z.array(fewShotSlotSchema),
});

export const formSchema = z.object({
  styleSummary: styleSummarySchema,
  promptPack: promptPackSchema,
});

export type FormValues = z.infer<typeof formSchema>;

type _StyleSummarySchemaExtendsContract = AssertExtends<
  z.output<typeof styleSummarySchema>,
  StyleSummary
>;
type _StyleSummaryContractExtendsSchema = AssertExtends<
  StyleSummary,
  z.output<typeof styleSummarySchema>
>;
type _PromptPackSchemaExtendsContract = AssertExtends<
  z.output<typeof promptPackSchema>,
  PromptPack
>;
type _PromptPackContractExtendsSchema = AssertExtends<
  PromptPack,
  z.output<typeof promptPackSchema>
>;

export function makeEmptyStyleSummary(): StyleSummary {
  return {
    style_name: "",
    style_positioning: "",
    core_features: [],
    lexical_preferences: [],
    rhythm_profile: [],
    punctuation_profile: [],
    imagery_and_themes: [],
    scene_strategies: [],
    avoid_or_rare: [],
    generation_notes: [],
  };
}

export function makeEmptyPromptPack(): PromptPack {
  return {
    system_prompt: "",
    scene_prompts: {
      dialogue: "",
      action: "",
      environment: "",
    },
    hard_constraints: [],
    style_controls: {
      tone: "",
      rhythm: "",
      evidence_anchor: "",
    },
    few_shot_slots: [],
  };
}
