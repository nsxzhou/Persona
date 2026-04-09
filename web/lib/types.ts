export type User = {
  id: string;
  username: string;
  created_at: string;
};

export type ProviderConfig = {
  id: string;
  label: string;
  base_url: string;
  default_model: string;
  api_key_hint: string;
  is_enabled: boolean;
  last_test_status: string | null;
  last_test_error: string | null;
  last_tested_at: string | null;
  created_at?: string;
  updated_at?: string;
};

export type ProviderSummary = {
  id: string;
  label: string;
  base_url: string;
  default_model: string;
  is_enabled: boolean;
};

export type Project = {
  id: string;
  name: string;
  description: string;
  status: "draft" | "active" | "paused";
  default_provider_id?: string;
  default_model: string;
  style_profile_id: string | null;
  archived_at: string | null;
  created_at?: string;
  updated_at?: string;
  provider: ProviderSummary;
};

export type StyleDimensionSummary = {
  vocabulary_habits: string;
  syntax_rhythm: string;
  narrative_perspective: string;
  dialogue_traits: string;
};

export type StyleScenePrompts = {
  dialogue: string;
  action: string;
  environment: string;
};

export type StyleFewShotExample = {
  type: string;
  text: string;
};

export type StyleDraft = {
  style_name: string;
  analysis_summary: string;
  global_system_prompt: string;
  dimensions: StyleDimensionSummary;
  scene_prompts: StyleScenePrompts;
  few_shot_examples: StyleFewShotExample[];
};

export type StyleSampleFile = {
  id: string;
  original_filename: string;
  content_type: string | null;
  byte_size: number;
  character_count: number | null;
  checksum_sha256: string;
  created_at: string;
  updated_at: string;
};

export type StyleAnalysisJob = {
  id: string;
  style_name: string;
  provider_id: string;
  model_name: string;
  status: "pending" | "running" | "succeeded" | "failed";
  stage: "cleaning" | "chunking" | "sampling" | "analyzing" | "assembling" | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  provider: ProviderSummary;
  sample_file: StyleSampleFile;
  draft: StyleDraft | null;
};

export type StyleProfile = StyleDraft & {
  id: string;
  source_job_id: string;
  provider_id: string;
  model_name: string;
  source_filename: string;
  created_at: string;
  updated_at: string;
};

export type SetupPayload = {
  username: string;
  password: string;
  provider: {
    label: string;
    base_url: string;
    api_key: string;
    default_model: string;
    is_enabled: boolean;
  };
};

export type LoginPayload = {
  username: string;
  password: string;
};

export type ProjectPayload = {
  name: string;
  description: string;
  status: "draft" | "active" | "paused";
  default_provider_id: string;
  default_model?: string;
  style_profile_id: string | null;
};

export type ProviderPayload = {
  label: string;
  base_url: string;
  api_key?: string;
  default_model: string;
  is_enabled: boolean;
};

export type StyleProfilePayload = StyleDraft & {
  job_id: string;
};
