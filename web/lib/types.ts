import type { components } from "@/lib/api/generated/openapi";

type OpenApiSchema<Name extends keyof components["schemas"]> = components["schemas"][Name];

export type User = OpenApiSchema<"UserResponse">;
export type ProviderConfig = OpenApiSchema<"ProviderConfigResponse">;
export type ProviderSummary = OpenApiSchema<"ProviderSummary">;
export type Project = OpenApiSchema<"ProjectResponse">;

export type AnalysisMeta = OpenApiSchema<"AnalysisMeta">;
export type AnalysisReportMarkdown = OpenApiSchema<"AnalysisReportMarkdown">;
export type StyleSummaryMarkdown = OpenApiSchema<"StyleSummaryMarkdown">;
export type PromptPackMarkdown = OpenApiSchema<"PromptPackMarkdown">;
export type StyleSampleFile = OpenApiSchema<"StyleSampleFileResponse">;

export const STYLE_ANALYSIS_JOB_STATUS = {
  PENDING: "pending",
  RUNNING: "running",
  PAUSED: "paused",
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

export type SetupPayload = components["schemas"]["SetupRequest"];
export type LoginPayload = components["schemas"]["LoginRequest"];
export type ProjectPayload = components["schemas"]["ProjectCreate"];
export type ProviderPayload = components["schemas"]["ProviderConfigCreate"];
export type ProviderUpdatePayload = components["schemas"]["ProviderConfigUpdate"];

export type StyleProfileCreatePayload = components["schemas"]["StyleProfileCreate"];
export type StyleProfileUpdatePayload = components["schemas"]["StyleProfileUpdate"];
