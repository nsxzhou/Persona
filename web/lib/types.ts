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

export type EvidenceSnippet = {
  excerpt: string;
  location: string;
};

export type ExecutiveSummary = {
  summary: string;
  representative_evidence: EvidenceSnippet[];
};

export type BasicAssessment = {
  text_type: string;
  multi_speaker: boolean;
  batch_mode: boolean;
  location_indexing: string;
  noise_handling: string;
};

export type SectionFinding = {
  label: string;
  summary: string;
  frequency: string;
  confidence: "high" | "medium" | "low";
  is_weak_judgment: boolean;
  evidence: EvidenceSnippet[];
};

export type AnalysisReportSection = {
  section: string;
  title: string;
  overview: string;
  findings: SectionFinding[];
};

export type AnalysisReport = {
  executive_summary: ExecutiveSummary;
  basic_assessment: BasicAssessment;
  sections: AnalysisReportSection[];
  appendix: string | null;
};

export type StyleSummarySceneStrategy = {
  scene: string;
  instruction: string;
};

export type StyleSummary = {
  style_name: string;
  style_positioning: string;
  core_features: string[];
  lexical_preferences: string[];
  rhythm_profile: string[];
  punctuation_profile: string[];
  imagery_and_themes: string[];
  scene_strategies: StyleSummarySceneStrategy[];
  avoid_or_rare: string[];
  generation_notes: string[];
};

export type StyleScenePrompts = {
  dialogue: string;
  action: string;
  environment: string;
};

export type PromptPackStyleControls = {
  tone: string;
  rhythm: string;
  evidence_anchor: string;
};

export type PromptPackFewShotSlot = {
  label: string;
  type: string;
  text: string;
  purpose: string;
};

export type PromptPack = {
  system_prompt: string;
  scene_prompts: StyleScenePrompts;
  hard_constraints: string[];
  style_controls: PromptPackStyleControls;
  few_shot_slots: PromptPackFewShotSlot[];
};

export type AnalysisMeta = {
  source_filename: string;
  model_name: string;
  text_type: string;
  has_timestamps: boolean;
  has_speaker_labels: boolean;
  has_noise_markers: boolean;
  uses_batch_processing: boolean;
  location_indexing: string;
  chunk_count: number;
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
  stage:
    | "classifying_input"
    | "analyzing_chunks"
    | "aggregating"
    | "reporting"
    | "summarizing"
    | "composing_prompt_pack"
    | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  provider: ProviderSummary;
  sample_file: StyleSampleFile;
  style_profile_id: string | null;
  analysis_meta: AnalysisMeta | null;
  analysis_report: AnalysisReport | null;
  style_summary: StyleSummary | null;
  prompt_pack: PromptPack | null;
};

export type StyleProfile = {
  id: string;
  source_job_id: string;
  provider_id: string;
  model_name: string;
  source_filename: string;
  style_name: string;
  analysis_report: AnalysisReport;
  style_summary: StyleSummary;
  prompt_pack: PromptPack;
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

export type StyleProfileCreatePayload = {
  job_id: string;
  style_summary: StyleSummary;
  prompt_pack: PromptPack;
};

export type StyleProfileUpdatePayload = {
  style_summary: StyleSummary;
  prompt_pack: PromptPack;
};
