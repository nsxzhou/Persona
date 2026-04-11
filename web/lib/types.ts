import type { components } from "@/lib/api/generated/openapi";

type OpenApiSchema<Name extends keyof components["schemas"]> = components["schemas"][Name];

export type User = OpenApiSchema<"UserResponse">;
export type ProviderConfig = OpenApiSchema<"ProviderConfigResponse">;
export type ProviderSummary = OpenApiSchema<"ProviderSummary">;
export type Project = OpenApiSchema<"ProjectResponse">;

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

export type StyleAnalysisJob = OpenApiSchema<"StyleAnalysisJobResponse">;
export type StyleAnalysisJobListItem = OpenApiSchema<"StyleAnalysisJobListItemResponse">;
export type StyleProfile = OpenApiSchema<"StyleProfileResponse">;
export type StyleProfileListItem = OpenApiSchema<"StyleProfileListItemResponse">;

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
