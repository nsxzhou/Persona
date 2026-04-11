import type { components } from "@/lib/api/generated/openapi";

type OpenApiSchema<Name extends keyof components["schemas"]> = components["schemas"][Name];

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

export type EvidenceSnippet = OpenApiSchema<"EvidenceSnippet">;
export type ExecutiveSummary = OpenApiSchema<"ExecutiveSummary">;
export type BasicAssessment = OpenApiSchema<"BasicAssessment">;
export type SectionFinding = OpenApiSchema<"SectionFinding">;
export type AnalysisReportSection = OpenApiSchema<"AnalysisReportSection">;
export type AnalysisReport = OpenApiSchema<"AnalysisReport">;
export type StyleSummarySceneStrategy = OpenApiSchema<"StyleSummarySceneStrategy">;
export type StyleSummary = OpenApiSchema<"StyleSummary">;
export type StyleScenePrompts = OpenApiSchema<"StyleScenePrompts">;
export type PromptPackStyleControls = OpenApiSchema<"PromptPackStyleControls">;
export type PromptPackFewShotSlot = OpenApiSchema<"PromptPackFewShotSlot">;
export type PromptPack = OpenApiSchema<"PromptPack">;
export type AnalysisMeta = OpenApiSchema<"AnalysisMeta">;
export type StyleSampleFile = OpenApiSchema<"StyleSampleFileResponse">;

export const STYLE_ANALYSIS_JOB_STATUS = {
  PENDING: "pending",
  RUNNING: "running",
  SUCCEEDED: "succeeded",
  FAILED: "failed",
} as const;

export type StyleAnalysisJobStatus =
  (typeof STYLE_ANALYSIS_JOB_STATUS)[keyof typeof STYLE_ANALYSIS_JOB_STATUS];

export const STYLE_ANALYSIS_JOB_STAGE = {
  PREPARING_INPUT: "preparing_input",
  ANALYZING_CHUNKS: "analyzing_chunks",
  AGGREGATING: "aggregating",
  REPORTING: "reporting",
  SUMMARIZING: "summarizing",
  COMPOSING_PROMPT_PACK: "composing_prompt_pack",
} as const;

export type StyleAnalysisJobStage =
  (typeof STYLE_ANALYSIS_JOB_STAGE)[keyof typeof STYLE_ANALYSIS_JOB_STAGE];

export const STYLE_ANALYSIS_JOB_PROCESSING_STATUSES = [
  STYLE_ANALYSIS_JOB_STATUS.PENDING,
  STYLE_ANALYSIS_JOB_STATUS.RUNNING,
] as const;

export type StyleAnalysisJob = {
  id: string;
  style_name: string;
  provider_id: string;
  model_name: string;
  status: StyleAnalysisJobStatus;
  stage: StyleAnalysisJobStage | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  provider: ProviderSummary;
  sample_file: StyleSampleFile;
  style_profile_id: string | null;
  analysis_meta?: AnalysisMeta | null;
  analysis_report?: AnalysisReport | null;
  style_summary?: StyleSummary | null;
  prompt_pack?: PromptPack | null;
  style_profile?: StyleProfile | null;
};

export type StyleAnalysisJobListItem = {
  id: StyleAnalysisJob["id"];
  style_name: StyleAnalysisJob["style_name"];
  provider_id: StyleAnalysisJob["provider_id"];
  model_name: StyleAnalysisJob["model_name"];
  status: StyleAnalysisJob["status"];
  stage: StyleAnalysisJob["stage"];
  error_message: StyleAnalysisJob["error_message"];
  started_at: StyleAnalysisJob["started_at"];
  completed_at: StyleAnalysisJob["completed_at"];
  created_at: StyleAnalysisJob["created_at"];
  updated_at: StyleAnalysisJob["updated_at"];
  provider: StyleAnalysisJob["provider"];
  sample_file: StyleAnalysisJob["sample_file"];
  style_profile_id: StyleAnalysisJob["style_profile_id"];
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

export type StyleProfileListItem = {
  id: string;
  provider_id: string;
  model_name: string;
  source_filename: string;
  style_name: string;
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
  mount_project_id?: string | null;
  style_summary: StyleSummary;
  prompt_pack: PromptPack;
};

export type StyleProfileUpdatePayload = OpenApiSchema<"StyleProfileUpdate">;
