import type { components } from "@/lib/api/generated/openapi";

type OpenApiSchema<Name extends keyof components["schemas"]> = components["schemas"][Name];

export type User = OpenApiSchema<"UserResponse">;
export type ProviderConfig = OpenApiSchema<"ProviderConfigResponse">;
export type Project = OpenApiSchema<"ProjectResponse">;
export type ProjectChapter = OpenApiSchema<"ProjectChapterResponse">;

export type AnalysisMeta = OpenApiSchema<"AnalysisMeta">;
export type AnalysisReportMarkdown = OpenApiSchema<"AnalysisReportMarkdown">;
export type StyleSummaryMarkdown = OpenApiSchema<"StyleSummaryMarkdown">;
export type PromptPackMarkdown = OpenApiSchema<"PromptPackMarkdown">;
export type StyleAnalysisJobLogs = OpenApiSchema<"StyleAnalysisJobLogsResponse">;

export type StyleAnalysisJob = OpenApiSchema<"StyleAnalysisJobResponse">;
export type StyleAnalysisJobListItem = OpenApiSchema<"StyleAnalysisJobBaseResponse">;
export type StyleAnalysisJobStatus = StyleAnalysisJob["status"];
export type StyleAnalysisJobStage = NonNullable<StyleAnalysisJob["stage"]>;
export type StyleProfile = OpenApiSchema<"StyleProfileResponse">;
export type StyleProfileListItem = OpenApiSchema<"StyleProfileListItemResponse">;
export type SetupStatusResponse = OpenApiSchema<"SetupStatusResponse">;
export type SetupResponse = OpenApiSchema<"SetupResponse">;
export type StyleAnalysisJobStatusSnapshot = OpenApiSchema<"StyleAnalysisJobStatusResponse">;
export type StyleAnalysisJobCreatePayload =
  Omit<components["schemas"]["Body_create_style_analysis_job_api_v1_style_analysis_jobs_post"], "file"> & {
    file: File;
  };
export type BeatGenerateResponse = OpenApiSchema<"BeatGenerateResponse">;
export type BibleUpdateResponse = OpenApiSchema<"BibleUpdateResponse">;
export type ConnectionTestResponse = OpenApiSchema<"ConnectionTestResponse">;

export type SetupPayload = components["schemas"]["SetupRequest"];
export type LoginPayload = components["schemas"]["LoginRequest"];
export type ProjectPayload = components["schemas"]["ProjectCreate"];
export type ProjectChapterUpdate = components["schemas"]["ProjectChapterUpdate"];
export type ProviderPayload = components["schemas"]["ProviderConfigCreate"];

export type StyleProfileCreatePayload = components["schemas"]["StyleProfileCreate"];
export type StyleProfileUpdatePayload = components["schemas"]["StyleProfileUpdate"];

export type ConceptGeneratePayload = components["schemas"]["ConceptGenerateRequest"];
export type ConceptGenerateResult = components["schemas"]["ConceptGenerateResponse"];
export type ConceptItem = components["schemas"]["ConceptItem"];
